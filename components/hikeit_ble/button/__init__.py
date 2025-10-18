import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button
from esphome.const import CONF_ID
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

HikeITButton = hikeit_ble_ns.class_("HikeITButton", button.Button, cg.Component)

CONF_COMMAND_TYPE = "command_type"

CONFIG_SCHEMA = button.button_schema(HikeITButton).extend({
    cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
    cv.Required(CONF_COMMAND_TYPE): cv.int_,
})

async def to_code(config):
    var = await button.new_button(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))
    cg.add(var.set_command_type(config[CONF_COMMAND_TYPE]))