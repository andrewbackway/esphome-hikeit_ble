import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button
from esphome.const import CONF_ID, CONF_ICON
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

DEPENDENCIES = ["hikeit_ble"]

ICON_MONITOR = "mdi:monitor"

CONF_COMMAND_TYPE = "command_type"

HikeITButton = hikeit_ble_ns.class_("HikeITButton", button.Button, cg.Component)

CONFIG_SCHEMA = (
    button.button_schema(HikeITButton, icon=ICON_MONITOR)
    .extend({
        cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
        cv.Optional(CONF_COMMAND_TYPE, default=0): cv.int_,
    })
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = await button.new_button(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))
    cg.add(var.set_command_type(config[CONF_COMMAND_TYPE]))
    # Register with parent based on command type
    if config[CONF_COMMAND_TYPE] == 0:
        cg.add(parent.set_screen_button(var))
    elif config[CONF_COMMAND_TYPE] == 1:
        cg.add(parent.set_auto_button(var))