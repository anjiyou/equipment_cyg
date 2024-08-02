
from secsgem.common import Message
from secsgem.gem.control_state_machine import ControlState
from secsgem.secs import SecsStreamFunction, SecsHandler

from equipment_cyg.controller.controller import Controller


"""    

"""


class ZhongChe(Controller):
    def __init__(self):
        super().__init__()
        self.enable_equipment()  # 启动MES服务

    def _on_s01f17(self, handler: SecsHandler, message: Message) -> SecsStreamFunction | None:
        """工厂发送S1F17请求设备在线."""
        del handler, message

        online_ack = 1  # 错误状态
        if self.control_state.current == ControlState.HOST_OFFLINE:
            self.control_state.remote_online()
            self.status_variables.get(501).value = ControlState.ONLINE_REMOTE.value  # 更新当前控制状态
            self.send_s6f11("control_state_changed")
            online_ack = 0  # 设备由host offline 变为 remote online, 会触发事件
        elif self.control_state.current in [
            ControlState.ONLINE, ControlState.ONLINE_LOCAL, ControlState.ONLINE_REMOTE
        ]:
            online_ack = 2  # 设备已是 remote online, 不会触发事件

        return self.stream_function(1, 18)(online_ack)

    def _on_s01f15(self, handler: SecsHandler, message: Message) -> SecsStreamFunction | None:
        """工厂发送S1F15请求设备离线, 控制状态变为online local."""
        del handler, message

        offline_ack = 2

        if self.control_state.current in [ControlState.ONLINE, ControlState.ONLINE_LOCAL, ControlState.ONLINE_REMOTE]:
            self.status_variables.get(500).value = self.control_state.current.value  # 更新前一次控制状态
            self.control_state.remote_offline()
            self.status_variables.get(501).value = self.control_state.current.value  # 更新当前控制状态
            self.send_s6f11("control_state_changed")
            offline_ack = 0

        return self.stream_function(1, 16)(offline_ack)

    def _on_rcmd_switch_control_state(self, **kwargs):
        switch_control_state = kwargs.get("control_state")
        if switch_control_state != self.control_state.current.value:
            self.status_variables.get(500).value = self.control_state.current.value  # 更新前一次控制状态
            if switch_control_state == 8:
                self.control_switch_online_remote()
            elif switch_control_state == 7:
                self.control_switch_online_local()
            self.status_variables.get(501).value = self.control_state.current.value  # 更新当前控制状态
            self.send_s6f11("control_state_changed")

    def _on_s02f23(self, handler: SecsHandler, message: Message) -> SecsStreamFunction | None:
        del handler
        parse_result = self.get_receive_data(message)
        return self.stream_function(2, 24)(1)
