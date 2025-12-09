# commands.py
# -*- coding: utf-8 -*-

import re
from jellylookup import lookup_jellycat_by_sku, JellyLookupError
from db import (
    add_to_wishlist,
    remove_from_wishlist,
    get_user_entries,
    count_for_sku,
    admin_remove_by_name,
    get_list_for_sku,
)


SKU_PATTERN = re.compile(r"[A-Z0-9]{3,10}")  # rough pattern for SKUs

def split_name_and_skus(arg_str: str):
    """
    Split a string into (name, SKUs).

    Example:
        "Alice Chen OT6SDP, C3CW"
        -> name = "Alice Chen"
           skus = ["OT6SDP", "C3CW"]

    Logic:
        - Find the first place a SKU-like token appears (via SKU_PATTERN).
        - Everything before that is treated as the name.
        - Everything from that position onward is parsed as SKUs.
    """
    m = SKU_PATTERN.search(arg_str)
    if not m:
        return None, []

    name = arg_str[:m.start()].strip()
    sku_part = arg_str[m.start():].strip()
    skus = parse_skus(sku_part)
    return name, skus



def parse_skus(arg_str: str):
    """
    Parse SKU codes from a string like 'OT6SDP, C3CW' or 'OT6SDP C3CW'.
    Returns a list of uppercased SKUs.
    """
    raw = re.split(r"[,\s]+", arg_str.strip())
    return [r.upper() for r in raw if r]

# 1) @add
def handle_add(user_id: str, display_name: str, text: str) -> str:
    """
    @add <SKU1>, <SKU2>...
    Example: @add BARL2BR, C3CW
    """
    arg_str = text[len("@add"):].strip()
    if not arg_str:
        return (
            "把想要找的Jellycat加入排隊清單吧！:\n"
            "請找到商品代碼加入排隊清單喔\n"
            "舉例: @add BARL2BR, C3CW \n"
        )

    skus = parse_skus(arg_str)
    if not skus:
        return "🤔請提供正確的Jellycat商品編號，例如：@add BARL2BR, C3CW"

    messages = []

    for sku in skus:
        try:
            info = lookup_jellycat_by_sku(sku)
        except JellyLookupError:
            messages.append(
                f"{sku}: 現在無法連線，請稍後再試一次"
            )
            continue

        if not info:
            messages.append(
                f"{sku}: ❌找不到此商品編號。\n"
                "請檢查是否輸入正確的編號 (如 BARL2BR) 並再試一次。"
            )
            continue

        pos = add_to_wishlist(
            user_id=user_id,
            display_name=display_name,
            sku=info["sku"],
            item_name=info["name"],
        )
        messages.append(f"🤍已將您加入{info['name']}（{info['sku']}）的排隊清單，目前排第 {pos} 位。")

    return "\n".join(messages)

def handle_admin_add(text: str) -> str:
    """
    Admin command:
        @adminadd <name> <SKU1>, <SKU2>...

    Example:
        @adminadd Alice Chen OT6SDP, C3CW

    Behavior:
        - Looks up each SKU on Jelly Journal.
        - Adds an entry to the wishlist using a synthetic user_id based on the name,
          so the name shows up like a real user entry.
    """
    arg_str = text[len("@adminadd"):].strip()
    if not arg_str:
        return (
            "🛠 管理員用法：@adminadd <名字> <SKU1>, <SKU2>...\n"
            "例如：@adminadd Alice Chen OT6SDP, C3CW"
        )

    name, skus = split_name_and_skus(arg_str)
    if not name:
        return "🤔 請先輸入名字，再輸入 SKU。\n例如：@adminadd Alice Chen OT6SDP"
    if not skus:
        return "🤔 看不出來有任何 SKU，請試試：@adminadd Alice Chen OT6SDP, C3CW"

    messages = []

    for sku in skus:
        try:
            info = lookup_jellycat_by_sku(sku)
        except JellyLookupError:
            messages.append(
                f"⚠️ {sku}：目前無法連線到 Jelly Journal，請稍後再試。"
            )
            continue

        if not info:
            messages.append(
                f"❌ {sku}：在 Jelly Journal 上找不到這個 SKU。"
            )
            continue

        # Use a synthetic user_id to represent an admin-added entry for this name
        manual_user_id = f"manual:{name}"

        pos = add_to_wishlist(
            user_id=manual_user_id,
            display_name=name,
            sku=info["sku"],
            item_name=info["name"],
        )
        messages.append(
            f"🧸 已將「{name}」加入「{info['name']}」（{info['sku']}）的心願清單，目前排第 {pos} 名。"
        )

    return "\n".join(messages)


# 2) @remove
def handle_remove(user_id: str, text: str) -> str:
    """
    @remove <SKU>
    """
    arg_str = text[len("@remove"):].strip()
    if not arg_str:
        return (
            "退出排隊清單:\n"
            "請找到商品代碼退出排隊清單喔\n"
            "舉例: @remove BARL2BR, C3CW \n"
        )

    skus = parse_skus(arg_str)
    if not skus:
        return "🤔請提供正確的Jellycat商品編號，例如：@remove BARL2BR, C3CW"

    sku = skus[0]
    item_name = remove_from_wishlist(user_id, sku)
    if item_name:
        return f"已將您從{item_name}的排隊清單中移除。"
    else:
        return f"您沒有加入{sku}的排隊清單喔！"


def handle_admin_remove(text: str) -> str:
    """
    Admin command:
        @adminremove <name> <SKU>

    Example:
        @adminremove Alice Chen OT6SDP

    Behavior:
        - Removes one entry for the given name on the given SKU
          (the earliest entry if multiple exist).
    """
    arg_str = text[len("@adminremove"):].strip()
    if not arg_str:
        return (
            "🛠 管理員用法：@adminremove <名字> <SKU>\n"
            "例如：@adminremove Alice Chen OT6SDP"
        )

    name, skus = split_name_and_skus(arg_str)
    if not name:
        return "🤔 請先輸入名字，再輸入 SKU。\n例如：@adminremove Alice Chen OT6SDP"
    if not skus:
        return "🤔 看不出來有任何 SKU，請試試：@adminremove Alice Chen OT6SDP"

    sku = skus[0]
    item_name = admin_remove_by_name(name, sku)

    if item_name:
        return f"🗑️ 已將「{name}」從「{item_name}」（{sku}）的心願清單中移除。"
    else:
        return f"❓ 在 {sku} 的心願清單中找不到名字「{name}」。"


# 3) @view
def handle_view(user_id: str) -> str:
    """
    @view
    """
    entries = get_user_entries(user_id)
    if not entries:
        return "您目前沒有任何排隊中的商品。\n請用 @add <SKU> 來加入一個吧！"

    lines = ["📋您的排隊清單："]
    for e in entries:
        lines.append(
            f"🤍{e['item_name']}（{e['sku']}）：您是第 {e['position']} 位，此列表共有 {e['total']} 人。"
        )
    return "\n".join(lines)


# 4) @count
def handle_count(text: str) -> str:
    """
    @count <SKU>
    """
    arg_str = text[len("@count"):].strip()
    if not arg_str:
        return (
            "查看特定商品的排隊清單:\n"
            "請找到商品代碼加入排隊清單喔\n"
            "舉例: @count BARL2BR \n"
        )

    skus = parse_skus(arg_str)
    if not skus:
        return "🤔 請提供正確的Jellycat商品代碼，例如：@count BARL2BR"

    sku = skus[0]
    total = count_for_sku(sku)

    item_label = sku  # default fallback
    try:
        info = lookup_jellycat_by_sku(sku)
        if info:
            item_label = f"{info['sku']} – {info['name']}"
    except JellyLookupError:
        item_label = sku

    if total == 0:
        return f"{item_label}：目前沒有人在這個排隊清單上，您可以當第一個喔！"
    elif total == 1:
        return f"{item_label}：目前只有 1 個人在排隊清單上。"
    else:
        return f"{item_label}：目前有 {total} 個人在排隊清單上。"


def handle_admin_list(text: str) -> str:
    """
    Admin command:
        @list <SKU>

    Example:
        @list OT6SDP

    Behavior:
        - Shows the full waiting list for the given SKU, in order.
        - Includes both SKU and item name in the header.
    """
    arg_str = text[len("@list"):].strip()
    if not arg_str:
        return "🧾 Admin usage: @list <SKU>\nExample: @list OT6SDP"

    skus = parse_skus(arg_str)
    if not skus:
        return "🤔 Please provide a valid SKU, e.g. @list OT6SDP"

    sku = skus[0]

    # Get all entries for this SKU
    rows = get_list_for_sku(sku)

    if not rows:
        return f"📭 {sku}: there is nobody on this wishlist yet."

    # Use the first row's item_name if available
    first = rows[0]
    item_name = first.get("item_name") or ""
    if item_name:
        header_label = f"{sku} – {item_name}"
    else:
        header_label = sku

    lines = [f"Waiting list for {header_label}:"]
    for i, row in enumerate(rows, start=1):
        display_name = row.get("display_name") or f"(user {row.get('user_id', '')[:8]})"
        lines.append(f"{i}. {display_name}")

    return "\n".join(lines)


