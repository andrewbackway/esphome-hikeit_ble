import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select
from esphome.const import CONF_ID, CONF_ICON
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID, SPEED_MODELS

DEPENDENCIES = ["hikeit_ble"]

ICON_SPEEDOMETER = "mdi:speedometer"

HikeITSpeedSelect = hikeit_ble_ns.class_("HikeITSpeedSelect", select.Select, cg.Component)

CONFIG_SCHEMA = (
    select.select_schema(HikeITSpeedSelect, icon=ICON_SPEEDOMETER)
    .extend({
        cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
    })
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = await select.new_select(config, options=SPEED_MODELS)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))
    cg.add(parent.set_speed_select(var))