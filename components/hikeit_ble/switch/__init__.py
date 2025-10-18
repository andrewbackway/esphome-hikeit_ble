import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch
from esphome.const import CONF_ID
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

HikeITLockedSwitch = hikeit_ble_ns.class_("HikeITLockedSwitch", switch.Switch, cg.Component)

CONFIG_SCHEMA = switch.switch_schema(HikeITLockedSwitch).extend({
    cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
})

async def to_code(config):
    var = await switch.new_switch(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))