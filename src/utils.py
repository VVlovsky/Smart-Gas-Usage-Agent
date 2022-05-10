from src.config import ETHER_protocols, POLYGON_protocols, AVALANCHE_protocols


def extract_argument(event: dict, argument: str) -> any:
    """
    the function extract specified argument from the event
    :param event: dict
    :param argument: str
    :return: argument value
    """
    return event.get('args', {}).get(argument, "")


def get_protocols_by_chain(chain_id):
    if chain_id == 1:
        return ETHER_protocols
    elif chain_id == 137:
        return POLYGON_protocols
    elif chain_id == 43114:
        return AVALANCHE_protocols


def get_key_by_value(my_dict: dict, value):
    return list(my_dict.keys())[[x.lower() for x in my_dict.values()].index(value)]


def get_full_info(object_inst):
    values = vars(object_inst)
    values['block'] = vars(values['block'])
    values['logs'] = [vars(log) for log in values['logs']]
    values['traces'] = [vars(trace) for trace in values['traces']]
    values['transaction'] = vars(values['transaction'])

    return values


def calculate_new_base_fee(base_fee, gas_limit, gas_used):
    gas_target = gas_limit // 2

    if gas_used == gas_target:
        return base_fee
    elif gas_used > gas_target:
        gas_used_delta = gas_used - gas_target
        base_fee_per_gas_delta = max(base_fee * gas_used_delta // gas_target // 8, 1)
        return base_fee + base_fee_per_gas_delta
    else:
        gas_used_delta = gas_target - gas_used
        base_fee_per_gas_delta = base_fee * gas_used_delta // gas_target // 8
        return base_fee - base_fee_per_gas_delta
