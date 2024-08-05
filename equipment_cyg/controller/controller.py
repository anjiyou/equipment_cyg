import csv
import datetime
import json
import logging
import os
import pathlib
import subprocess
import threading
from logging.handlers import TimedRotatingFileHandler
from typing import Union

from secsgem.common import DeviceType, Message
from secsgem.gem import CollectionEvent, GemEquipmentHandler, EquipmentConstant, StatusVariable, RemoteCommand, Alarm
from secsgem.secs.data_items.tiack import TIACK
from secsgem.secs.variables import U4, Array
from secsgem.hsms import HsmsSettings, HsmsConnectMode

from equipment_cyg.controller.enum_sece_data_type import EnumSecsDataType

from equipment_cyg.utils.database.log_handler import DatabaseHandler
from equipment_cyg.utils.database.operations import get_all_event, get_all_equipment_constant, get_all_status_variable, \
    get_all_remote_command, get_all_alarm


class Controller(GemEquipmentHandler):
    def __init__(self, **kwargs):
        self.config = self.get_config(self.get_config_path(f'{"/".join(self.__module__.split("."))}.conf'))
        self._file_handler = None  # 保存日志的处理器

        hsms_settings = HsmsSettings(
            address=self.get_value_from_config("secs_ip"),
            port=self.get_value_from_config("secs_port"),
            connect_mode=getattr(HsmsConnectMode, self.get_value_from_config("connect_mode")),
            device_type=DeviceType.EQUIPMENT
        )
        super().__init__(settings=hsms_settings, **kwargs)

        self.model_name = self.config.get("model_name")
        self.software_version = self.config.get("software_version")

        self.initial_log_config()
        self.initial_evnet()
        self.initial_equipment_constant()
        self.initial_status_variable()
        self.initial_remote_command()
        self.initial_alarm()

    # 初始化函数
    def initial_log_config(self) -> None:
        """保存所有 self.__module__ + "." + self.__class__.__name__ 日志和sec通讯日志."""
        self.create_log_dir()
        self.logger.addHandler(self.file_handler)  # 所有 self.__module__ + "." + self.__class__.__name__ 日志
        self.protocol.communication_logger.addHandler(self.file_handler)  # secs 通讯日志

        if self.config.get("config_from_db", False):
            db_handler = DatabaseHandler()  # 创建保存日志到数据库处理器
            db_handler.setFormatter(logging.Formatter(self.get_log_format()))
            self.logger.addHandler(db_handler)

    def initial_evnet(self):
        """加载定义好的事件."""
        if self.config.get("config_from_db", False):
            event_list = get_all_event()
            for event_id, event_name in event_list:
                self.collection_events.update({event_id: CollectionEvent(event_id, event_name, [])})
        else:
            collection_events = self.config.get("collection_events", {})
            for event_name, event_info in collection_events.items():
                self.collection_events.update({
                    event_name: CollectionEvent(name=event_name, data_values=[], **event_info)
                })

    def initial_equipment_constant(self):
        """加载定义好的设备常量."""
        if self.config.get("config_from_db", False):
            ec_list = get_all_equipment_constant()
            for ec_id, name, min_value, max_value, default_value, value_type, unit, callback in ec_list:
                self.equipment_constants.update({
                    ec_id: EquipmentConstant(
                        ec_id, name, min_value, max_value, default_value, unit, value_type, callback
                    )
                })
        else:
            pass

    def initial_status_variable(self):
        """加载定义好的变量."""
        if self.config.get("config_from_db", False):
            svs = get_all_status_variable()
            for sv_id, sv_name, unit, value_type, callback in svs:
                self.status_variables.update({sv_id: StatusVariable(sv_id, sv_name, unit, value_type, callback)})
        else:
            status_variables = self.config.get("status_variable", {})
            for sv_name, sv_info in status_variables.items():
                sv_id = sv_info.get("svid")
                value_type_str = sv_info.get("value_type")
                value_type = getattr(EnumSecsDataType, value_type_str).value
                sv_info["value_type"] = value_type
                self.status_variables.update({sv_id: StatusVariable(name=sv_name, **sv_info)})
                sv_info["value_type"] = value_type_str

    def initial_remote_command(self):
        """加载定义好的远程命令."""
        if self.config.get("config_from_db", False):
            rcs = get_all_remote_command()
            for rc_code, rc_name, ce_id, rc_param_names in rcs:
                self.remote_commands.update({rc_name: RemoteCommand(rc_code, rc_name, rc_param_names, ce_id)})
        else:
            remote_commands = self.config.get("remote_commands", {})
            for rc_name, rc_info in remote_commands.items():
                ce_id = rc_info.get("ce_id")
                self.remote_commands.update({rc_name: RemoteCommand(name=rc_name, ce_finished=ce_id, **rc_info)})

    def initial_alarm(self):
        """加载定义好的报警."""
        if self.config.get("config_from_db", False):
            alarms = get_all_alarm()
            for alarm_id, alarm_name, alarm_text, alarm_code, ce_on, ce_off in alarms:
                self.alarms.update({alarm_id: Alarm(alarm_id, alarm_name, alarm_text, alarm_code, ce_on, ce_off)})
        else:
            if alarm_path := self.get_config_path(self.config.get("alarm_csv")):
                with pathlib.Path(alarm_path).open("r", encoding="utf-8") as file:
                    csv_reader = csv.reader(file)
                    next(csv_reader)
                    for row in csv_reader:
                        alarm_id, alarm_name, alarm_text, alarm_code, ce_on, ce_off, *_ = row
                        self.alarms.update({
                            alarm_id: Alarm(alarm_id, alarm_name, alarm_text, alarm_code, ce_on, ce_off)
                        })

    # host给设备发送指令

    def _on_s02f17(self, handler, packet):
        """获取设备时间."""
        del handler, packet
        return self.stream_function(2, 18)(datetime.datetime.now().strftime("%Y%m%d%H%M%S%C"))

    def _on_s02f31(self, handler, packet):
        """设置设备时间."""
        del handler
        function = self.settings.streams_functions.decode(packet)
        parser_result = function.get()
        date_time_str = parser_result
        if len(date_time_str) not in (14, 16):
            self.logger.info(f"***设置失败*** --> 时间格式错误: {date_time_str} 不是14或16个数字！")
            return self.stream_function(2, 32)(1)
        current_time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S%C")
        self.logger.info(f"***当前时间*** --> 当前时间: {current_time_str}")
        self.logger.info(f"***设置时间*** --> 设置时间: {date_time_str}")
        status = self.set_date_time(date_time_str)
        current_time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S%C")
        if status:
            self.logger.info(f"***设置成功*** --> 当前时间: {current_time_str}")
            ti_ack = TIACK.ACK
        else:
            self.logger.info(f"***设置失败*** --> 当前时间: {current_time_str}")
            ti_ack = TIACK.TIME_SET_FAIL
        return self.stream_function(2, 32)(ti_ack)

    def _on_s07f01(self, handle, packet):
        """host发送s07f01,下载配方请求前询问,调用此函数."""
        raise NotImplementedError("如果使用,这个方法必须要根据产品重写！")

    def _on_s07f03(self, handle, packet):
        """host发送s07f03,下发配方名及主体body,调用此函数."""
        raise NotImplementedError("如果使用,这个方法必须要根据产品重写！")

    def _on_s07f05(self, handler, packet):
        """host请求配方列表"""
        raise NotImplementedError("如果使用,这个方法必须要根据产品重写！")

    def _on_s07f17(self, handler, packet):
        """删除配方."""
        raise NotImplementedError("如果使用,这个方法必须要根据产品重写！")

    def _on_s07f19(self, handler, packet):
        """host请求配方列表."""
        raise NotImplementedError("如果使用,这个方法必须要根据产品重写！")

    def _on_s10f03(self, handler, packet):
        """host terminal display signal, need override."""
        raise NotImplementedError("如果使用,这个方法必须要根据产品重写！")

    # 通用函数
    def send_s6f11(self, event_name):
        """给EAP发送S6F11事件.

        Args:
            event_name (str): 事件名称.
        """

        def _ce_sender():
            reports = []
            event = self.collection_events.get(event_name)
            link_reports = event.link_reports
            for report_id, sv_ids in link_reports.items():
                variables = []
                for sv_id in sv_ids:
                    sv_instance: StatusVariable = self.status_variables[sv_id]
                    if issubclass(sv_instance.value_type, Array):
                        value = sv_instance.value
                        variables += value
                    else:
                        value = sv_instance.value_type(sv_instance.value)
                        variables.append(value)
                reports.append({"RPTID": U4(report_id), "V": variables})

            self.send_and_waitfor_response(
                self.stream_function(6, 11)({"DATAID": 1, "CEID": event.ceid, "RPT": reports})
            )

        threading.Thread(target=_ce_sender, daemon=True).start()

    def enable_equipment(self):
        """启动监控EAP连接的服务."""
        self.enable()  # 设备和host通讯
        self.logger.info(f"*** CYG SECSGEM 服务已启动 *** -> 等待工厂 EAP 连接!")

    def get_value_from_config(self, key) -> Union[str, int, dict, None]:
        """根据key获取配置文件里的值.

        Args:
            key(str): 获取值对应的key.

        Returns:
            Union[str, int, dict]: 从配置文件中获取的值.
        """
        return self.config.get(key, None)

    def get_receive_data(self, message: Message) -> Union[dict, str]:
        """解析Host发来的数据并返回.

        Args:
            message (Message): Host发过来的数据包实例.

        Returns:
            Union[dict, str]: 解析后的数据.
        """
        function = self.settings.streams_functions.decode(message)
        return function.get()

    # 静态通用函数
    @staticmethod
    def get_config_path(relative_path) -> str:
        """获取配置文件绝对路径地址."""
        return f'{os.path.dirname(__file__)}/../../{relative_path}'

    @staticmethod
    def get_config(path) -> dict:
        """获取配置文件内容."""
        conf_path = pathlib.Path(path)
        with conf_path.open(mode="r", encoding="utf-8") as f:
            conf_dict = json.load(f)
        return conf_dict

    @staticmethod
    def update_config(path, data: dict) -> None:
        """更新配置文件内容."""
        conf_path = pathlib.Path(path)
        with conf_path.open(mode="w+", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def set_date_time(modify_time_str) -> bool:
        """设置windows系统日期和时间.

        Args:
            modify_time_str (str): 要修改的时间字符串.

        Returns:
            bool: 修改成功或者失败.
        """
        date_time = datetime.datetime.strptime(modify_time_str, "%Y%m%d%H%M%S%f")
        date_command = f"date {date_time.year}-{date_time.month}-{date_time.day}"
        result_date = subprocess.run(date_command, shell=True)
        time_command = f"time {date_time.hour}:{date_time.minute}:{date_time.second}"
        result_time = subprocess.run(time_command, shell=True)
        if result_date.returncode == 0 and result_time.returncode == 0:
            return True
        return False

    @staticmethod
    def get_log_format():
        return "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"

    @staticmethod
    def create_log_dir():
        """判断log目录是否存在, 不存在就创建."""
        log_dir = pathlib.Path(f"{os.getcwd()}/log")
        if not log_dir.exists():
            os.mkdir(log_dir)

    @property
    def file_handler(self):
        if self._file_handler is None:
            logging.basicConfig(level=logging.INFO, encoding="UTF-8", format=self.get_log_format())
            log_file_name = f"{os.getcwd()}/log/{datetime.datetime.now().strftime('%Y-%m-%d')}"
            self._file_handler = TimedRotatingFileHandler(
                log_file_name, when="D", interval=1, backupCount=10, encoding="UTF-8"
            )
            self._file_handler.setFormatter(logging.Formatter(self.get_log_format()))
        return self._file_handler
