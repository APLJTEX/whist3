from playcard import *
import random


def find_valid_cards(hand, lead_suit):
    """找出手中所有符合'跟花色'规则的牌。"""
    if lead_suit is None:  # 首攻，可以出任意牌
        return hand[:]
    return [card for card in hand if get_suit(card) == lead_suit]


def find_highest_card(cards, trump_suit=None, lead_suit=None):
    """
    找出一组牌中的最高牌。
    如果指定了 trump_suit，则王牌 > 其他花色。
    如果未指定 trump_suit，则只在 lead_suit 花色内比较。
    """
    if not cards:
        return None

    # 如果有王牌，只在王牌中找最高的
    if trump_suit is not None:
        trumps = [c for c in cards if get_suit(c) == trump_suit]
        if trumps:
            return max(trumps, key=get_rank_ace_high)

    # 否则，在引导花色中找最高的
    if lead_suit is not None:
        same_suit = [c for c in cards if get_suit(c) == lead_suit]
        if same_suit:
            return max(same_suit, key=get_rank_ace_high)

    # 默认情况
    return max(cards, key=get_rank_ace_high)


def determine_trick_winner(trick, trump_suit, leader_index=0):
    """
    判定一墩的赢家。
    trick: [(player, card), ...] 当前墩的出牌列表
    trump_suit: 王牌花色
    leader_index: 首攻者在trick列表中的索引（通常是0）
    返回: 赢家的玩家名 (e.g., 'north')
    """
    lead_suit = get_suit(trick[leader_index][1])
    winning_card = find_highest_card([c for _, c in trick], trump_suit, lead_suit)
    for player, card in trick:
        if card == winning_card:
            return player
    return trick[0][0]  # fallback


def ai_play_card(player, hand, current_trick, trump_suit, game_state):
    """
    AI出牌决策函数。
    实现：强制跟花、高效赢墩、主动清短套。
    """
    #  确定引导花色
    lead_suit = None
    if current_trick:
        lead_suit = get_suit(current_trick[0][1])  # 首攻者的花色

    # 找出所有合法的牌
    valid_cards = find_valid_cards(hand, lead_suit)

    # 如果必须跟花色
    if lead_suit is not None and valid_cards != hand:
        # 计算当前墩中该花色的最大牌
        same_suit_cards = [card for _, card in current_trick if get_suit(card) == lead_suit]
        if same_suit_cards:
            highest_in_suit = max(same_suit_cards, key=get_rank_ace_high)
        else:
            highest_in_suit = None

        # 尝试用刚好能赢的最小牌
        if highest_in_suit is not None:
            winning_cards = [c for c in valid_cards if get_rank_ace_high(c) > get_rank_ace_high(highest_in_suit)]
            if winning_cards:
                return min(winning_cards, key=get_rank_ace_high)  # 用最小的赢牌

        # 如果不能赢，就垫最小的牌
        return min(valid_cards, key=get_rank_ace_high)

    # 如果首攻或无同花色
    # 首先，尝试清掉一个短套（非王牌花色）
    suit_counts = {}
    for card in hand:
        s = get_suit(card)
        suit_counts[s] = suit_counts.get(s, 0) + 1

    # 移除王牌花色，我们通常不想先出王牌
    non_trump_suits = {s: count for s, count in suit_counts.items() if s != trump_suit}
    if non_trump_suits:
        shortest_suit = min(non_trump_suits, key=non_trump_suits.get)
        shortest_suit_cards = [c for c in hand if get_suit(c) == shortest_suit]
        if shortest_suit_cards:
            # 出该花色中最小的牌
            return min(shortest_suit_cards, key=get_rank_ace_high)

    # 如果没有好的短套可清，就出最小的非王牌
    non_trump_cards = [c for c in hand if get_suit(c) != trump_suit]
    if non_trump_cards:
        return min(non_trump_cards, key=get_rank_ace_high)

    # 出王牌（通常是小王牌）
    trump_cards = [c for c in hand if get_suit(c) == trump_suit]
    if trump_cards:
        return min(trump_cards, key=get_rank_ace_high)

    # fallback
    return valid_cards[0]


# ====== 游戏流程 ======
def new_game(session):
    """初始化一局新游戏。"""
    deck = make_deck()
    random.shuffle(deck)

    # 发牌给四家
    hands = {
        'north': deck[0:13],
        'east': deck[13:26],
        'south': deck[26:39],
        'west': deck[39:52]
    }

    # 最后一张牌（发给东家的最后一张）决定王牌
    trump_suit = get_suit(deck[51])

    game_state = {
        'hands': hands,
        'trump_suit': trump_suit,
        'scores': {'south_north': 0, 'east_west': 0},
        'tricks': [],  # 已完成的墩
        'current_trick': [],  # 当前正在打的墩
        'leader': 'north',  # 首攻者是北家
        'message': f"New game started! Trump suit is {trump_suit}. North leads.",
        'message_class': "info-message",
        'stop_type': 'lead_card'
    }

    session['game_state'] = game_state
    return game_state


def game_update(session, action):
    """处理游戏中的每一个动作。"""
    game_state = session.get('game_state')
    if not game_state:
        return new_game(session)

    players = ['north', 'east', 'south', 'west']
    current_trick = game_state.get('current_trick', [])
    hands = game_state['hands']
    trump_suit = game_state['trump_suit']
    leader = game_state['leader']

    # 确定轮到谁出牌
    next_player_index = len(current_trick)
    next_player = players[(players.index(leader) + next_player_index) % 4]

    # --- 人类玩家 ---
    if next_player == 'south':
        played_card = action
        # 验证出牌是否合法
        lead_suit = get_suit(current_trick[0][1]) if current_trick else None
        valid_cards = find_valid_cards(hands['south'], lead_suit)
        if played_card not in valid_cards:
            game_state['message'] = "Invalid move! You must follow suit."
            game_state['message_class'] = "error-message"
            session['game_state'] = game_state
            return

        # 从手牌中移除这张牌并加入当前墩
        hands['south'].remove(played_card)
        current_trick.append(('south', played_card))

    # --- AI玩家 ---
    else:
        ai_card = ai_play_card(next_player, hands[next_player], current_trick, trump_suit, game_state)
        hands[next_player].remove(ai_card)
        current_trick.append((next_player, ai_card))
        game_state['message'] = f"{next_player.capitalize()} played {ai_card}."

    # --- 检查是否完成一墩 ---
    if len(current_trick) == 4:
        winner = determine_trick_winner(current_trick, trump_suit)
        # 更新分数
        if winner in ['south', 'north']:
            game_state['scores']['south_north'] += 1
        else:
            game_state['scores']['east_west'] += 1

        # 保存此墩，并重置下一墩
        game_state['tricks'].append(current_trick)
        game_state['current_trick'] = []
        game_state['leader'] = winner  # 赢家领出下一墩

        # 检查游戏是否结束
        if len(game_state['tricks']) == 13:
            sn_score = game_state['scores']['south_north']
            ew_score = game_state['scores']['east_west']
            if sn_score >= 7:
                game_state['message'] = f"South-North wins the game! Final score: {sn_score}-{ew_score}"
            else:
                game_state['message'] = f"East-West wins the game! Final score: {ew_score}-{sn_score}"
            game_state['stop_type'] = 'game_over'
        else:
            game_state['message'] = f"{winner.capitalize()} wins the trick! They will lead the next one."
            game_state['stop_type'] = 'new_trick'

    else:
        # 墩未完成，继续
        game_state['current_trick'] = current_trick
        # 判断下一个玩家是谁
        next_next_player = players[(players.index(next_player) + 1) % 4]
        if next_next_player == 'south':
            game_state['stop_type'] = 'follow_card' if current_trick else 'lead_card'
        else:
            pass

    game_state['hands'] = {
        'north': hands['north'],
        'east': hands['east'],
        'south': hands['south'],
        'west': hands['west']
    }

    session['game_state'] = game_state