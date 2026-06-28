from playcard import *
import random


def find_valid_cards(hand, lead_suit):
    """找出手中所有符合'跟花色'规则的牌。"""
    if lead_suit is None:  # 首攻，可以出任意牌
        return hand[:]
    return [card for card in hand if get_suit(card) == lead_suit]


def sort_hand(hand):
    """对一手牌进行排序：先按花色(♣, ♢, ♡, ♠)，再按点数(A, K, Q, J, 10...)"""
    # 定义花色排序优先级
    suit_order = {'C': 0, 'D': 1, 'H': 2, 'S': 3}  # Clubs, Diamonds, Hearts, Spades
    
    # 按花色和点数排序
    return sorted(hand, key=lambda card: (suit_order[get_suit(card)], 
                                        -get_rank_ace_high(card)))


def get_card_display_name(card):
    """将内部牌表示转换为人类可读的名称"""
    rank = get_rank_ace_high(card)
    suit = get_suit(card)
    
    # 转换点数
    rank_names = {
        '14': 'Ace',
        '13': 'King',
        '12': 'Queen',
        '11': 'Jack',
        '10': '10',
        '9': '9',
        '8': '8',
        '7': '7',
        '6': '6',
        '5': '5',
        '4': '4',
        '3': '3',
        '2': '2'
    }
    
    # 转换花色
    suit_names = {
        'C': 'Clubs',
        'D': 'Diamonds',
        'H': 'Hearts',
        'S': 'Spades'
    }
    
    # 获取可读名称
    rank_name = rank_names.get(str(rank), str(rank))
    suit_name = suit_names.get(suit, suit)
    
    return f"{rank_name} of {suit_name}"


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
    # 确定引导花色
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

    # 发牌顺序：北 → 东 → 南 → 西 （顺时针）
    hands = {
        'north': deck[0:13],
        'east': deck[13:26],
        'south': deck[26:39],
        'west': deck[39:52]
    }

    # 最后一张牌作为王牌
    trump_card = deck[51]
    trump_suit = get_suit(trump_card)
    
    # 王牌花色映射
    trump_svg_map = {
        'S': {'svg': 'spade', 'name': 'Spade', 'symbol': '♠'},
        'H': {'svg': 'heart', 'name': 'Heart', 'symbol': '♥'},
        'D': {'svg': 'diamond', 'name': 'Diamond', 'symbol': '♦'},
        'C': {'svg': 'club', 'name': 'Club', 'symbol': '♣'}
    }
    trump_info = trump_svg_map.get(trump_suit, trump_svg_map['S'])
    
    # 玩家显示名称
    players = {
        'north': 'North (AI)',
        'east': 'East (AI)',
        'south': 'South (You)',
        'west': 'West (AI)'
    }
    
    # 游戏开始消息
    suit_names = {'S': 'Spades', 'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs'}
    game_message = f"Trump suit is {suit_names.get(trump_suit, trump_suit)}! Ready for a new trick."

    # 对手牌进行排序
    sorted_hands = {
        'north': sort_hand(hands['north']),
        'east': sort_hand(hands['east']),
        'south': sort_hand(hands['south']),
        'west': sort_hand(hands['west'])
    }

    game_state = {
        'hands': sorted_hands,
        'trump_suit': trump_suit,
        'trump_card': trump_card,
        'scores': {'south_north': 0, 'east_west': 0},
        'tricks': [],
        'current_trick': [],  # 用于存储当前墩的出牌
        'leader': 'north',  # 首攻者是北家
        'players': players,
        'trump_suit_name': trump_info['svg'],
        'message': game_message,
        'message_class': "info-message",
        'stop_type': 'new_trick',
        'trick_number': 1,
        'trick_history': []  # 用于存储所有出牌历史
    }

    session['game_state'] = game_state
    return game_state


def game_update(session, action):
    """处理游戏中的每一个动作。"""
    game_state = session.get('game_state')
    if not game_state:
        return new_game(session)

    # ====== 关键修正：使用逆时针出牌顺序 ======
    # 逆时针顺序：North → West → South → East
    players = ['north', 'west', 'south', 'east']
    
    current_trick = game_state.get('current_trick', [])
    hands = game_state['hands']
    trump_suit = game_state['trump_suit']
    leader = game_state['leader']

    # --- 处理"New Trick"动作 ---
    if action == 'new_trick':
        # 重置当前墩
        game_state['current_trick'] = []
        game_state['leader'] = 'north'  # 北家首攻
        game_state['message'] = "New trick started. North leads."
        
        # 清空历史记录
        game_state['trick_history'] = []
        
        # 直接触发自动出牌
        game_state['stop_type'] = 'auto_play'
        session['game_state'] = game_state
        return game_update(session, None)  # 直接触发自动出牌

    # --- 处理AI自动出牌动作 ---
    if action == 'auto_play' or game_state.get('stop_type') == 'auto_play':
        # 确定当前轮到谁出牌
        next_player_index = len(current_trick)
        next_player = players[(players.index(leader) + next_player_index) % 4]
        
        # ====== 关键修正：确保出牌信息正确存储 ======
        # 如果是AI玩家的回合，自动出牌
        if next_player != 'south':
            # AI出牌
            ai_card = ai_play_card(next_player, hands[next_player], current_trick, trump_suit, game_state)
            hands[next_player].remove(ai_card)
            hands[next_player] = sort_hand(hands[next_player])
            
            # ====== 关键修正：正确添加出牌信息 ======
            current_trick.append((next_player, ai_card))
            game_state['current_trick'] = current_trick
            
            # ====== 关键修正：使用正确的显示位置映射 ======
            # 定义玩家到显示位置的映射
            player_to_position = {
                'north': 0,  # 顶部
                'west': 1,   # 左侧
                'south': 2,  # 底部
                'east': 3    # 右侧
            }
            
            # 获取正确的显示位置
            display_position = player_to_position[next_player]
            
            # 更新出牌历史
            game_state['trick_history'].append({
                'player': next_player,
                'card': ai_card,
                'display_position': display_position,  # 使用正确的显示位置
                'display_name': get_card_display_name(ai_card)
            })
            
            # 显示人类可读的出牌信息
            display_name = get_card_display_name(ai_card)
            game_state['message'] = f"{next_player.capitalize()} played {display_name}."
            
            # 检查是否完成一墩
            if len(current_trick) == 4:
                winner = determine_trick_winner(current_trick, trump_suit)
                # 更新分数
                if winner in ['south', 'north']:
                    game_state['scores']['south_north'] += 1
                else:
                    game_state['scores']['east_west'] += 1

                # 保存此墩
                trick_dict = {}
                for player, card in current_trick:
                    trick_dict[player] = card
                game_state['tricks'].append(trick_dict)
                game_state['current_trick'] = []
                game_state['leader'] = winner
                game_state['trick_number'] = len(game_state['tricks']) + 1

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
                    game_state['stop_type'] = 'follow_card'
                else:
                    # 下一个玩家还是AI，继续自动出牌
                    game_state['stop_type'] = 'auto_play'
                    # 立即触发下一次出牌
                    return game_update(session, 'auto_play')
        
        # 更新手牌
        game_state['hands'] = {
            'north': hands['north'],
            'east': hands['east'],
            'south': hands['south'],
            'west': hands['west']
        }
        
        session['game_state'] = game_state
        return game_state

    # --- 人类玩家出牌 ---
    else:
        # ... 人类玩家出牌逻辑保持不变 ...
        # 但需要确保出牌后也更新trick_history
        played_card = action
        # 验证出牌是否合法
        lead_suit = get_suit(current_trick[0][1]) if current_trick else None
        valid_cards = find_valid_cards(hands['south'], lead_suit)
        if played_card not in valid_cards:
            game_state['message'] = "Invalid move! You must follow suit."
            game_state['message_class'] = "error-message"
            session['game_state'] = game_state
            return game_state

        # 从手牌中移除这张牌并加入当前墩
        hands['south'].remove(played_card)
        hands['south'] = sort_hand(hands['south'])
        current_trick.append(('south', played_card))
        game_state['current_trick'] = current_trick
        
        # ====== 关键修正：使用正确的显示位置映射 ======
        # 定义玩家到显示位置的映射
        player_to_position = {
            'north': 0,  # 顶部
            'west': 1,   # 左侧
            'south': 2,  # 底部
            'east': 3    # 右侧
        }
        
        # 获取正确的显示位置
        display_position = player_to_position['south']
        
        # 更新出牌历史
        display_name = get_card_display_name(played_card)
        game_state['trick_history'].append({
            'player': 'south',
            'card': played_card,
            'display_position': display_position,  # 使用正确的显示位置
            'display_name': display_name
        })
        
        game_state['message'] = f"You played {display_name}."

        # 检查是否完成一墩
        if len(current_trick) == 4:
            winner = determine_trick_winner(current_trick, trump_suit)
            # 更新分数
            if winner in ['south', 'north']:
                game_state['scores']['south_north'] += 1
            else:
                game_state['scores']['east_west'] += 1

            # 保存此墩
            trick_dict = {}
            for player, card in current_trick:
                trick_dict[player] = card
            game_state['tricks'].append(trick_dict)
            game_state['current_trick'] = []
            game_state['leader'] = winner
            game_state['trick_number'] = len(game_state['tricks']) + 1

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
            next_next_player = players[(players.index('south') + 1) % 4]
            if next_next_player == 'south':
                game_state['stop_type'] = 'follow_card'
            else:
                # 下一个玩家是AI，继续自动出牌
                game_state['stop_type'] = 'auto_play'
                # 立即触发下一次出牌
                return game_update(session, 'auto_play')

        # 更新手牌
        game_state['hands'] = {
            'north': hands['north'],
            'east': hands['east'],
            'south': hands['south'],
            'west': hands['west']
        }
        
        session['game_state'] = game_state
        return game_state
