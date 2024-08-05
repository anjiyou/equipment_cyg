"""
控制状态改变:
    1.实时监控 plc current_control_state 地址位
    2.和python的 current_control_state 比较, 不相等等触发 control_state_change 事件

运行状态改变:
    1.实时监控 plc current_machine_state 地址位
    2.和python的 current_machine_state 比较, 不相等等触发 machine_state_change 事件

开工单:
    1.在页面上点击开工单按钮, lot_id = new_lot
    2.触发 new_lot 事件条件
        1.监控 plc track_in_signal 地址位信号, 是 True
        2.监控 plc new_lot_signal 地址位信号, 是 True
        3.读取 label_id_origin 赋值给 python的 lot_id

进站:
    1.监控 plc track_in_signal 地址位, 是 True
    2.读取 plc label_id_origin 地址位, 赋值给python的 label_id_origin
    3.触发 track_in 事件, 判断 label_id_origin 是否等于 lot_id
        1.等于: track_in_result -> OK: 0
            向 plc track_in_result 信号地址位 写 0
        2.不等于: track_in_result -> NG: 1
            向 plc track_in_result 信号地址位 写 1

打印标签:
    1.监控 plc label_id_print_request_signal 地址位, 是 True
    2.向 plc label_id_print 地址位写python的 label_id_origin 值
    3.触发 print_label 事件

track_out:
    1.监控 plc track_out_signal 地址位, 是 True
    2.读取 plc label_id_print_camera 地址位, 赋值给python的 label_id_print
    3.触发 track_out 事件, 判断 label_id_origin 是否等于 label_id_print
        1.等于: track_out -> OK: 0
            向 plc track_out_result 地址位 写 0
        2.不等于: track_out -> NG: 1
            向 plc track_out_result 地址位 写 1
"""
from equipment_cyg.controller.controller import Controller


class Ceribell(Controller):
    def __init__(self):
        super().__init__()
        print()