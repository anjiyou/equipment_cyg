from equipment_cyg.controller.controller import Controller


"""    
设备启动:
    PC->EAP: 将设备控制状态发给EAP, S6F11
        1001: control state local
        1002: control state remote
        1003: controller offline
        
操作员将大托盘放在上料位, 大托盘带有4列黑盒tray, 每个黑盒tray放有10个产品
 
操作员扫描工单号
    PC->EAP: 开工单发给EAP, S6F11
        2001: new lot, sv: lot_id
    EAP->PC: 返回是否有上一个工单的尾料,  S2F41 remote_command: has_rest, params: rest_id=xxxx
        如果 rest_id 不为空代表有尾料
            1.将尾料的标签写入plc
            2.操作员拿到尾料然后扫描尾料箱上的码
                PC->EAP: 将尾料码发给EAP, S6F11
                    2003: rest code verification, sv: rest_code
            3.将尾料放在指定位置
        如果 rest_id 为空, 进行下一步
    EAP->PC: 选择配方, S2F41 remote_command: pp_select, params: recipe_name=xxxx
        将选择的配方信息写入到plc
    PC->EAP: 配方选择成功, S6F11  
        2002: pp select success, sv: recipe_name

操作员点击开始按钮
    PC->EAP: 请求开始工作， S6F11 
        2004: start work inquire, sv: recipe_name 
    EAP->PC: 可以开始工作, S2F41 remote_command: start_work, params: None
        将可以开始信号写入plc   
    PC->EAP: process state状态改变, S6F11
        1000: process state changed   
        
报警
    PC->EAP: 报警和解除报警, S5F1 
    
操作员点击停止按钮
    PC->EAP: 请求停止工作, S6F11 
        2005: stop work inquire, sv: recipe_name 
    EAP->PC: 可以停止, S2F41 remote_command: stop_work, params: recipe_name=xxx
        将结束信号写入plc
    PC->EAP: process state状态改变, S6F11
        1000: process state changed   

设备将产品从黑盒tray转到白盒tray扫描每个产品的码
    PC->EAP: 将产品码发给EAP判断产品是否OK, S6F11
        2006: 产品码检查, sv: 产品码 
    EAP->PC: 产品码检查结果, S2F41 remote_command: product_code_verify, params: result=xxx
        result=1, 则放入白盒tray
        result=-1, 则放入NG的tray
        
保压后外观检查
    检查通过:
        PC->EAP: 将外观检查结果发给EAP, S6F11
            2007: 外观检查, sv: 检查结果
    检查不通过
        PC->EAP: 将外观检查结果发给EAP, S6F11
            2007: 外观检查, sv: 检查结果
        PC->EAP: 报警, S5F1
        
给装有白盒tray的箱子贴标签
    PC->EAP: 标签信息和箱子里的10个产品码绑定发给EAP, S6F11
        2008: 箱子标签和10和产品码绑定, sv: 标签码, 10个产品列表
        
工单结束
    EAP->PC: 工单结束, S2F41 remote_command: lot_stop, params: lot_id=xxx
        将结束信号写入plc
    PC->EAP: process state状态改变, S6F11
        1000: process state changed
"""


class Infineon(Controller):
    pass
