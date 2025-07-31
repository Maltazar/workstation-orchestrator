from typing import Dict, Any, Optional, List
from copy import deepcopy


def merge_lists(base_list: List[Any], override_list: List[Any]) -> List[Any]:
    """Merge two lists, handling both simple types and dicts."""
    result = deepcopy(base_list)

    for item in override_list:
        if isinstance(item, dict):
            # For dict items, check if there's a matching item in base_list
            # and merge them, otherwise append
            found = False
            for i, base_item in enumerate(result):
                if isinstance(base_item, dict) and base_item.get("name") == item.get(
                    "name"
                ):
                    result[i] = {**base_item, **item}
                    found = True
                    break
            if not found:
                result.append(deepcopy(item))
        elif item not in result:
            result.append(deepcopy(item))

    return result


def deep_merge_dicts(
    base: Dict[str, Any], override: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries, with override taking precedence.
    Lists are merged with special handling for dictionary items.
    """
    if override is None:
        return deepcopy(base)

    result = deepcopy(base)

    for key, value in override.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge_dicts(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key] = merge_lists(result[key], value)
            else:
                result[key] = deepcopy(value)
        else:
            result[key] = deepcopy(value)

    return result


def deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge two dictionaries, with override taking precedence.
    Lists are combined, nested dictionaries are merged recursively.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # Combine lists, removing duplicates if items are hashable
                try:
                    result[key] = list(dict.fromkeys(result[key] + value))
                except TypeError:  # For unhashable types
                    result[key] = result[key] + value
            else:
                result[key] = value
        else:
            result[key] = value

    return result
