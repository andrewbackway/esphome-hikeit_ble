import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.const import CONF_ID, CONF_ICON
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

DEPENDENCIES = ["hikeit_ble"]

ICON_TUNE = "mdi:tune-vertical"

HikeITStepNumber = hikeit_ble_ns.class_("HikeITStepNumber", number.Number, cg.Component)

CONFIG_SCHEMA = (
    number.number_schema(HikeITStepNumber, icon=ICON_TUNE)
    .extend({
        cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
    })
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = await number.new_number(config, min_value=0, max_value=15, step=1)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))
    cg.add(parent.set_step_number(var))