import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.const import CONF_ID
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

HikeITStepNumber = hikeit_ble_ns.class_("HikeITStepNumber", number.Number, cg.Component)

CONFIG_SCHEMA = number.number_schema(HikeITStepNumber).extend({
    cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
})

async def to_code(config):
    var = await number.new_number(config, min_value=0, max_value=15, step=1)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))