#声明：以下内容均使用agent按给定逻辑生成

import time
import random

# ==================== 参数配置 ====================
# 压力计算权重
CAR_WEIGHT = 4      # 车辆数乘4作为车辆初始积压强度
PED_WEIGHT = 2      # 行人数乘2作为行人最终积压强度（初始人数×2倍系数）

# 固定配时（双方压力均为0时）
FIXED_GREEN = 20    # 绿灯20秒

# 安全切灯程序（绿灯闪3秒 → 黄灯闪3秒 → 红灯持续2秒 → 切灯）
SAFE_GREEN_FLASH = 3
SAFE_YELLOW_FLASH = 3
SAFE_ALL_RED = 2

# 直接切灯程序（绿灯闪3秒 → 红灯持续2秒 → 切灯，无黄灯）
DIRECT_GREEN_FLASH = 3
DIRECT_ALL_RED = 2

# 单方向有压力时的阈值
SINGLE_MAX_GREEN = 40          # 绿灯最长40秒
SINGLE_PRESSURE_RATIO = 0.25   # 压力降至原强度的0.25倍

# 双方向有压力，当前绿灯方向压力大
BIG_CURRENT_MAX_GREEN = 40
BIG_CURRENT_PRESSURE_RATIO = 0.25

# 双方向有压力，红灯方向压力大（≥2倍）
BIG_OTHER_GRACE = 10               # 给当前绿灯10秒宽限
BIG_OTHER_NEW_MAX_GREEN = 45       # 新方向绿灯最长45秒
BIG_OTHER_NEW_PRESSURE_RATIO = 0.4 # 新方向压力降至原强度的0.4倍

# 双方向有压力，红灯方向压力大（<2倍）
SMALL_OTHER_GRACE = 10
SMALL_OTHER_NEW_MAX_GREEN = 35
SMALL_OTHER_NEW_PRESSURE_RATIO = 0.5

# 仿真速度（秒），调小可加速演示
TICK_INTERVAL = 0.1


class TrafficLightController:
    def __init__(self):
        # 当前相位: "AC"（车辆） 或 "BD"（行人）
        self.phase = "AC"
        # 状态: "GREEN", "GREEN_FLASH", "YELLOW_FLASH", "ALL_RED"
        self.state = "GREEN"
        self.timer = 0

        # 绿灯开始时的压力值（用于计算比例）
        self.green_start_pressure = 0
        # 绿灯模式: "NORMAL", "BIG_PRESSURE", "SMALL_DIFF"
        self.green_mode = "NORMAL"

        # 宽限倒计时（给当前绿灯方向的10秒宽限）
        self.grace_timer = 0

        # 切灯后要去的相位
        self.next_phase = "BD"
        # 切灯类型: "SAFE"（安全切灯） 或 "DIRECT"（直接切灯）
        self.switch_type = "SAFE"
        # 下一个绿灯的模式（用于宽限后新方向的特殊规则）
        self.next_green_mode = "NORMAL"

        # 传感器模拟：车辆数和行人数
        self.car_count = 0
        self.ped_count = 0

        # 日志
        self.log = []

    def get_pressure(self):
        """返回加权后的压力值：(AC车辆压力, BD行人压力)"""
        stress_car = self.car_count * CAR_WEIGHT
        stress_ped = self.ped_count * PED_WEIGHT
        return stress_car, stress_ped

    def get_current_pressure(self):
        """获取当前绿灯相位的压力值"""
        stress_car, stress_ped = self.get_pressure()
        return stress_car if self.phase == "AC" else stress_ped

    def get_other_pressure(self):
        """获取另一相位的压力值"""
        stress_car, stress_ped = self.get_pressure()
        return stress_ped if self.phase == "AC" else stress_car

    def update_sensors(self):
        """模拟传感器数据变化（可替换为真实计算机视觉输入）"""
        # 随机到达：每秒有一定概率增加车辆或行人
        if random.random() < 0.2:
            self.car_count += random.randint(1, 3)
        if random.random() < 0.2:
            self.ped_count += random.randint(1, 3)

        # 绿灯放行，压力减少
        if self.state == "GREEN":
            if self.phase == "AC":
                self.car_count = max(0, self.car_count - random.randint(1, 2))
            else:
                self.ped_count = max(0, self.ped_count - random.randint(1, 2))

    def decide(self):
        """
        在 GREEN 状态下进行切灯决策。
        返回: (action, next_phase, reason)
        action: "HOLD"（保持绿灯）, "SWITCH_SAFE"（安全切灯）,
                "SWITCH_DIRECT"（直接切灯）, "GRACE"（进入宽限）
        """
        current_p = self.get_current_pressure()
        other_p = self.get_other_pressure()
        other_phase = "BD" if self.phase == "AC" else "AC"

        # 宽限期间不决策
        if self.grace_timer > 0:
            return "HOLD", None, ""

        # 特殊绿灯模式（宽限后切过来的新方向）
        if self.green_mode == "BIG_PRESSURE":
            # 直到强度小于原本的0.4倍或时间达到45秒
            if current_p <= self.green_start_pressure * BIG_OTHER_NEW_PRESSURE_RATIO or self.timer >= BIG_OTHER_NEW_MAX_GREEN:
                return "SWITCH_SAFE", other_phase, (
                    f"BIG_PRESSURE模式：压力{current_p:.0f}≤{self.green_start_pressure*BIG_OTHER_NEW_PRESSURE_RATIO:.0f}"
                    f" 或 绿灯{self.timer}s≥{BIG_OTHER_NEW_MAX_GREEN}s"
                )
            return "HOLD", None, ""

        if self.green_mode == "SMALL_DIFF":
            if current_p <= self.green_start_pressure * SMALL_OTHER_NEW_PRESSURE_RATIO or self.timer >= SMALL_OTHER_NEW_MAX_GREEN:
                return "SWITCH_SAFE", other_phase, (
                    f"SMALL_DIFF模式：压力{current_p:.0f}≤{self.green_start_pressure*SMALL_OTHER_NEW_PRESSURE_RATIO:.0f}"
                    f" 或 绿灯{self.timer}s≥{SMALL_OTHER_NEW_MAX_GREEN}s"
                )
            return "HOLD", None, ""

        # ===== 情况1：双方压力都为0 =====
        if current_p == 0 and other_p == 0:
            if self.timer >= FIXED_GREEN:
                return "SWITCH_SAFE", other_phase, f"双方无压力，绿灯满{FIXED_GREEN}秒"
            return "HOLD", None, ""

        # ===== 情况2：当前绿灯方向无压力，红灯方向有压力 =====
        if current_p == 0 and other_p > 0:
            return "SWITCH_DIRECT", other_phase, "当前绿灯无压力，红灯有压力，直接切灯"

        # ===== 情况3：当前绿灯方向有压力，红灯方向无压力 =====
        if current_p > 0 and other_p == 0:
            # 延长绿灯，直到压力降为0（下一tick自动进入其他情况）
            return "HOLD", None, ""

        # ===== 情况4：双方向均有压力 =====
        if current_p >= other_p:
            # 当前绿灯方向压力大
            if self.timer >= BIG_CURRENT_MAX_GREEN or current_p <= self.green_start_pressure * BIG_CURRENT_PRESSURE_RATIO:
                return "SWITCH_SAFE", other_phase, (
                    f"双方向，绿灯方向压力大：绿灯{self.timer}s≥{BIG_CURRENT_MAX_GREEN}s"
                    f" 或 压力{current_p:.0f}≤{self.green_start_pressure*BIG_CURRENT_PRESSURE_RATIO:.0f}"
                )
            return "HOLD", None, ""
        else:
            # 红灯方向压力大
            if other_p >= 2 * current_p:
                # 差距≥2倍：给当前绿灯10秒宽限，新方向用 BIG_PRESSURE 规则
                self.grace_timer = BIG_OTHER_GRACE
                self.next_green_mode = "BIG_PRESSURE"
                return "GRACE", other_phase, (
                    f"红灯方向压力{other_p:.0f}≥2×{current_p:.0f}，给{self.grace_timer}秒宽限"
                )
            else:
                # 差距<2倍：给当前绿灯10秒宽限，新方向用 SMALL_DIFF 规则
                self.grace_timer = SMALL_OTHER_GRACE
                self.next_green_mode = "SMALL_DIFF"
                return "GRACE", other_phase, (
                    f"红灯方向压力大但不足2倍，给{self.grace_timer}秒宽限"
                )

    def tick(self):
        """每秒调用一次，推进状态机"""
        self.update_sensors()

        if self.state == "GREEN":
            if self.grace_timer > 0:
                # 宽限倒计时
                self.grace_timer -= 1
                if self.grace_timer == 0:
                    # 宽限结束，触发安全切灯
                    self.switch_type = "SAFE"
                    self.state = "GREEN_FLASH"
                    self.timer = 0
                    self.log.append(f"  [宽限结束] 进入安全切灯程序，目标相位 {self.next_phase}")
            else:
                action, next_phase, reason = self.decide()
                if action == "HOLD":
                    pass
                elif action == "SWITCH_SAFE":
                    self.switch_type = "SAFE"
                    self.next_phase = next_phase
                    self.state = "GREEN_FLASH"
                    self.timer = 0
                    self.log.append(f"  [决策] {reason} → 安全切灯，目标 {self.next_phase}")
                elif action == "SWITCH_DIRECT":
                    self.switch_type = "DIRECT"
                    self.next_phase = next_phase
                    self.state = "GREEN_FLASH"
                    self.timer = 0
                    self.log.append(f"  [决策] {reason} → 直接切灯，目标 {self.next_phase}")
                elif action == "GRACE":
                    self.next_phase = next_phase
                    self.log.append(f"  [决策] {reason} → 宽限 {self.grace_timer} 秒，目标 {self.next_phase}")
            self.timer += 1

        elif self.state == "GREEN_FLASH":
            self.timer += 1
            if self.timer >= (SAFE_GREEN_FLASH if self.switch_type == "SAFE" else DIRECT_GREEN_FLASH):
                if self.switch_type == "SAFE":
                    self.state = "YELLOW_FLASH"
                    self.timer = 0
                    self.log.append("  [切灯] 绿闪结束，进入黄闪")
                else:
                    self.state = "ALL_RED"
                    self.timer = 0
                    self.log.append("  [切灯] 绿闪结束，进入全红")

        elif self.state == "YELLOW_FLASH":
            self.timer += 1
            if self.timer >= SAFE_YELLOW_FLASH:
                self.state = "ALL_RED"
                self.timer = 0
                self.log.append("  [切灯] 黄闪结束，进入全红")

        elif self.state == "ALL_RED":
            self.timer += 1
            if self.timer >= (SAFE_ALL_RED if self.switch_type == "SAFE" else DIRECT_ALL_RED):
                # 切换相位
                self.phase = self.next_phase
                self.state = "GREEN"
                self.timer = 0
                # 记录新绿灯开始时的压力
                self.green_start_pressure = self.get_current_pressure()
                # 设置绿灯模式（可能是宽限后切过来的特殊模式）
                self.green_mode = self.next_green_mode
                self.next_green_mode = "NORMAL"  # 重置
                self.log.append(
                    f"  [切灯完成] 现在 {self.phase} 方向绿灯，"
                    f"模式 {self.green_mode}，初始压力 {self.green_start_pressure:.0f}"
                )

    def get_light_icons(self):
        """返回当前 AC 和 BD 的灯态图标"""
        if self.state in ("GREEN", "GREEN_FLASH"):
            if self.phase == "AC":
                return "🟢", "🔴"
            else:
                return "🔴", "🟢"
        elif self.state == "YELLOW_FLASH":
            if self.phase == "AC":
                return "🟡", "🔴"
            else:
                return "🔴", "🟡"
        else:  # ALL_RED
            return "🔴", "🔴"


def main():
    random.seed(2026)  # 固定随机种子，方便复现
    ctrl = TrafficLightController()

    print("=" * 80)
    print("智能红绿灯调度仿真（AC=车辆，BD=行人）")
    print(f"车辆压力 = 车辆数 × {CAR_WEIGHT}，行人压力 = 行人数 × {PED_WEIGHT}")
    print("=" * 80)
    print()

    for t in range(300):  # 仿真300秒
        ctrl.tick()
        stress_car, stress_ped = ctrl.get_pressure()
        ac_light, bd_light = ctrl.get_light_icons()

        print(
            f"T={t:3d}s | AC:{ac_light} BD:{bd_light} | "
            f"车压:{stress_car:3.0f} 人压:{stress_ped:3.0f} | "
            f"状态:{ctrl.state:12s} | 相位:{ctrl.phase} | "
            f"模式:{ctrl.green_mode:12s} | 计时:{ctrl.timer:2d}s"
        )

        # 输出本 tick 产生的日志
        for entry in ctrl.log:
            print(entry)
        ctrl.log = []

        time.sleep(TICK_INTERVAL)

    print()
    print("=" * 80)
    print("仿真结束")
    print("=" * 80)


if __name__ == "__main__":
    main()