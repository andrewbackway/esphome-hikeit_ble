#pragma once
#include "esphome/components/number/number.h"
#include "../hikeit_ble.h"

namespace esphome {
namespace hikeit_ble {

class HikeITStepNumber : public number::Number, public Component {
 public:
  void set_parent(HikeITBLEComponent *parent) { this->parent_ = parent; }
  
 protected:
  void control(float value) override {
    if (this->parent_ != nullptr) {
      uint8_t step = (uint8_t)value;
      SpeedModel model = this->parent_->get_last_message().speed_model;
      this->parent_->send_step_command(step, model);
    }
  }
  
  HikeITBLEComponent *parent_{nullptr};
};

}  // namespace hikeit_ble
}  // namespace esphome