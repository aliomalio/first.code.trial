import sys

class GoGame:
    def __init__(self, size=19):
        if size not in (9, 13, 19):
            raise ValueError('Board size must be 9, 13, or 19')
        self.size = size
        self.board = [[0 for _ in range(size)] for _ in range(size)]
        self.captured = {1: 0, 2: 0}
        self.turn = 1  # 1 for Black, 2 for White

    def display_board(self):
        letters = 'ABCDEFGHJKLMNOPQRST'[:self.size]
        header = '   ' + ' '.join(letters)
        print(header)
        for row in range(self.size):
            line = []
            for col in range(self.size):
                stone = self.board[row][col]
                if stone == 1:
                    line.append('X')
                elif stone == 2:
                    line.append('O')
                else:
                    line.append('.')
            print(f'{row+1:2} ' + ' '.join(line))
        print(f"Captured - Black: {self.captured[2]} White: {self.captured[1]}")

    def neighbors(self, row, col):
        for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
            r, c = row+dr, col+dc
            if 0 <= r < self.size and 0 <= c < self.size:
                yield r, c

    def group(self, row, col):
        color = self.board[row][col]
        visited = set()
        stack = [(row, col)]
        group = []
        liberties = set()
        while stack:
            r, c = stack.pop()
            if (r, c) in visited:
                continue
            visited.add((r, c))
            group.append((r, c))
            for nr, nc in self.neighbors(r, c):
                if self.board[nr][nc] == 0:
                    liberties.add((nr, nc))
                elif self.board[nr][nc] == color and (nr, nc) not in visited:
                    stack.append((nr, nc))
        return group, liberties

    def remove_group(self, group):
        color = self.board[group[0][0]][group[0][1]]
        for r, c in group:
            self.board[r][c] = 0
        self.captured[3-color] += len(group)

    def place_stone(self, row, col):
        if self.board[row][col] != 0:
            print('Invalid move: position occupied.')
            return False
        color = self.turn
        self.board[row][col] = color
        to_capture = []
        for nr, nc in self.neighbors(row, col):
            if self.board[nr][nc] == 3 - color:
                group, liberties = self.group(nr, nc)
                if not liberties:
                    to_capture.append(group)
        # check self capture
        group, liberties = self.group(row, col)
        if not liberties and not to_capture:
            self.board[row][col] = 0
            print('Invalid move: self capture.')
            return False
        for grp in to_capture:
            self.remove_group(grp)
        self.turn = 3 - self.turn
        return True

    def parse_move(self, move):
        letters = 'ABCDEFGHJKLMNOPQRST'[:self.size]
        if len(move) < 2:
            return None
        col_letter = move[0].upper()
        if col_letter not in letters:
            return None
        try:
            row = int(move[1:]) - 1
        except ValueError:
            return None
        col = letters.index(col_letter)
        if 0 <= row < self.size:
            return row, col
        return None

    def play(self):
        print(f'Starting Go game {self.size}x{self.size}. X=Black O=White')
        while True:
            self.display_board()
            player = 'Black' if self.turn == 1 else 'White'
            move = input(f'{player} move (e.g., D4 or "quit" to exit): ')
            if move.lower() == 'quit':
                print('Game ended.')
                break
            pos = self.parse_move(move)
            if pos is None:
                print('Invalid input.')
                continue
            if self.place_stone(*pos):
                continue

if __name__ == '__main__':
    size = 19
    if len(sys.argv) > 1:
        try:
            size = int(sys.argv[1])
        except ValueError:
            print('Invalid board size. Using 19.')
            size = 19
    game = GoGame(size)
    game.play()
