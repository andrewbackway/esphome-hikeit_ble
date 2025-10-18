import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select
from esphome.const import CONF_ID
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

HikeITSpeedSelect = hikeit_ble_ns.class_("HikeITSpeedSelect", select.Select, cg.Component)

CONFIG_SCHEMA = select.select_schema(HikeITSpeedSelect).extend({
    cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
})

async def to_code(config):
    var = await select.new_select(config, options=[])
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))