def get_hw_model_as_number(hw_model):
    return int.from_bytes(hw_model.encode(), 'little')

