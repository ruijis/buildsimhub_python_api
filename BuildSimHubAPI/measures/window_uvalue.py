from .model_action import ModelAction


class WindowUValue(ModelAction):
    # this shows the ip to si conversion rate
    # if unit is 'ip', then multiply this rate.
    # for window it is the U-value
    # convert U-value IP to SI
    CONVERSION_RATE = 0.17612

    def __init__(self, unit="si", orientation=None):

        if orientation is None:
            ModelAction.__init__(self, 'window_uvalue', unit)
            self._measure_name = 'Window_U'
        else:
            orientation = orientation.lower()
            if orientation == 'w':
                ModelAction.__init__(self, 'window_uvalue_w', unit)
                self._measure_name = 'Window_U_West'
            elif orientation == 'e':
                ModelAction.__init__(self, 'window_uvalue_e', unit)
                self._measure_name = 'Window_U_East'
            elif orientation == 's':
                ModelAction.__init__(self, 'window_uvalue_s', unit)
                self._measure_name = 'Window_U_South'
            elif orientation == 'n':
                ModelAction.__init__(self, 'window_uvalue_n', unit)
                self._measure_name = 'Window_U_North'
            else:
                ModelAction.__init__(self, 'window_uvalue', unit)
                self._measure_name = 'Window_U'
        self._lower_limit = 0
        self._measure_help = '''
        measure name: Window_U_[Orientation]
        Unit: ip or si
        Minimum: 0.1
        Maximum: NA
        Type: numeric

        This measure will update the U value of the window in WindowMaterial:SimpleGlazingSystem 
        It is suggested to use this function with Window SHGC measure - if the Window U-Value is not present
        and the original model uses detail window layer method, then this measure could create a new simple glazing system
        with a default SHGC.
        '''

    def _unit_convert_ratio(self):
        return WindowUValue.CONVERSION_RATE
