from forta_agent import Finding, FindingType, FindingSeverity
from src.utils import get_key_by_value


class UncertainPriorityFeeFindings:

    @staticmethod
    def critical(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'Critical Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is critically higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE-UNCERTAIN',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.Critical,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'estimated_min_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })

    @staticmethod
    def high(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'High Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is much higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE-UNCERTAIN',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.High,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'estimated_min_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })

    @staticmethod
    def medium(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'Average Higher Then Excepted Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is average higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE-UNCERTAIN',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.Medium,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'estimated_min_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })

    @staticmethod
    def low(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'A Little Bit Higher Then Excepted Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'may be a little bit higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE-UNCERTAIN',
            'type': FindingType.Info,
            'severity': FindingSeverity.Low,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'estimated_min_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })


class PriorityFeeFindings:

    @staticmethod
    def critical(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'Critical Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is critically higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.Critical,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'real_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })

    @staticmethod
    def high(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'High Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is much higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.High,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'real_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })

    @staticmethod
    def medium(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'Average Higher Then Excepted Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is average higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE',
            'type': FindingType.Info,
            'severity': FindingSeverity.Medium,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'real_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })

    @staticmethod
    def low(protocols, protocol, excepted_max_fee, real_min_priority_fee, tx_hash):
        name = get_key_by_value(my_dict=protocols, value=protocol)
        return Finding({
            'name': f'A Little Bit Higher Then Excepted Priority Fee for {name}',
            'description': f'Priority fee for {name} '
                           f'is a little bit higher than excepted!',
            'alert_id': 'SMART-PRIORITY-FEE',
            'type': FindingType.Info,
            'severity': FindingSeverity.Low,
            'metadata': {
                'protocol_address': protocol,
                'excepted_max_fee': excepted_max_fee / 10 ** 9,
                'real_priority_fee': real_min_priority_fee / 10 ** 9,
                'tx_hash': tx_hash,
            }
        })
