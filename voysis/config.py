import configparser
import os
from string import Template

Config = configparser.ConfigParser()
GENERAL = 'general'
AUTH = 'auth'
HTTP = 'http'
WS = 'ws'
MIC = 'mic'

_converters = {
    bool: lambda x: 'true' == str(x).lower(),
    int: int,
    float: float
}


def apply_config(to_obj, section):
    """
    Applies the details of a config section to an object. This function
    iterates through the keys in a section and determines if +to_obj+ has
    an attribute defined by that name. If it does, it assigns the value of
    the config property to the object. If the attribute already has a value
    assigned to it, an attempt will be made to convert the configuration
    property's value to the same type before assigning it.
    :param to_obj: The object to apply configuration to.
    :param section: The section to read properties from.
    :return: None
    """
    if section not in Config:
        return
    for key, value in Config.items(section):
        try:
            if hasattr(to_obj, key):
                default_value = getattr(to_obj, key)
                converter = _converters.get(type(default_value), lambda v: v)
                setattr(to_obj, key, converter(value))
        except Exception:
            pass


def load_config(config_file):
    """
    Load config file
    :return:
    """
    if len(Config.read(config_file)) < 1:
        raise ValueError('Failed to parse config file')

def get(section, name, default):
    try:
        value = Template(Config.get(section, name))
        return value.substitute(os.environ)
    except:
        return default

def get_int(section, name, default):
    try:
        value = get(section, name, str(default))
        return int(value)
    except:
        return default

def get_float(section, name, default):
    try:
        value = get(section, name, str(default))
        return float(value)
    except:
        return default

def get_boolean(section, name, default):
    try:
        value = Config.getboolean(section, name)
        return value
    except:
        return default


