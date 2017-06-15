# A custom tado component for home-assistant
Custom home-assistant component for tado (using my fork of PyTado for a py3 compatible module)

It is highly inspired by https://community.home-assistant.io/t/tado-api-json/272/5 and the comments by diplix (https://community.home-assistant.io/users/diplix)

It is called `tado_v1` because it is build upon the unofficial API used by the myTado.com-Webapp. It has been merged as `tado` component in hass main repository, but I will leave this here for those willing to use a custom component and to do some testing on new features or bug-fixes.

# Howto use
I created a new custom_component which adds multiple sensors for every zone in myTado.com (not for every device, tado is build around zones!)

## Copy files to local config directory
you have to copy all files included in `custom_components` to your home-assistant config directory.

For hass manual installation it is:

  `/home/homeassistant/.homeassistant/`
  
## Edit configuration.yaml
```
tado_v1:
    username: <.. your username ..>
    password: <.. your password ..>
```

## Use the new sensors in home-assistant
It creates a sensor for the bridge
```
sensor.<name of tado home>_tado_bridge_status  (boolean)
```

and one climate device for every zone
```
climate.<name of tado zone>
```
with the capabilities of changeing the temperature setting and the tado mode for manual changes. Manually setting the away mode is not supported, because you cannot set the away mode in mytado.com.

The following operation modes are supported
```
    CONST_OVERLAY_MANUAL: 'Manual',
    CONST_OVERLAY_TIMER: 'Timer',
    CONST_OVERLAY_TADO_MODE: 'Tado mode',
    CONST_MODE_SMART_SCHEDULE: 'Smart schedule',
    CONST_MODE_OFF: 'Off',
```

For devices supporting `FAN_MODES` (like ac devices), you can set the following fan modes:
```
    CONST_MODE_FAN_HIGH: 'High',
    CONST_MODE_FAN_MIDDLE: 'Middle',
    CONST_MODE_FAN_LOW: 'Low',
    CONST_MODE_OFF: 'Off',
```

# Links
* Home-Assistant (http://home-assistant.io)
* PyTado (https://github.com/chrism0dwk/PyTado) -> (https://github.com/wmalgadey/PyTado)
