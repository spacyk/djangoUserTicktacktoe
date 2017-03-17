from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

GAME_STATUS_CHOICES = (
    ('A', 'Active'),
    ('F', 'First Player Wins'),
    ('S', 'Second Player Wins'),
    ('D', 'Draw')
)

FIRST_PLAYER_MOVE = 'X'
SECOND_PLAYER_MOVE = 'O'
BOARD_SIZE = 3

# inherits from models.Manager
# a bit weird syntax - need to look into this
class GamesManager(models.Manager):
    def games_for_user(self, user):
        return super(GamesManager, self).get_queryset().filter(
            Q(first_player_id=user.id) | Q(second_player_id=user.id))

    def new_game(self, invitation):
        game = Game(first_player=invitation.to_user,
                    second_player=invitation.from_user,
                    next_to_move=invitation.to_user)
        return game


class Game(models.Model):
    first_player = models.ForeignKey(User, related_name="games_first_player")
    second_player = models.ForeignKey(User, related_name="games_second_player")
    next_to_move = models.ForeignKey(User, related_name="games_to_move")
    start_time = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=1, default='A', choices=GAME_STATUS_CHOICES)
    objects = GamesManager()

    def as_board(self):
        board = [['' for x in range(BOARD_SIZE)] for y in range(BOARD_SIZE)]
        for move in self.move_set.all():
            board[move.y][move.x] = FIRST_PLAYER_MOVE if move.by_first_player else SECOND_PLAYER_MOVE
        return board

    def create_move(self):
        return Move(game=self, by_first_player=(self.next_to_move == self.first_player))

    def update_after_move(self, move):
        self.toogle_next_player()
        self.status = self.get_status(move)

    def get_status(self, last_move):
        board = self.as_board()
        x = last_move.x
        y = last_move.y
        board[y][x] = FIRST_PLAYER_MOVE if last_move.by_first_player else SECOND_PLAYER_MOVE

        if (board[y][0] == board[y][1] == board[y][2]) or \
            (board[0][x] == board[1][x] == board[2][x]):
            return "F" if last_move.by_first_player else "S"

        if (y == x) or (abs(y-x) == 2):
            if (board[0][0] == board[1][1] == board[2][2]) or \
                (board[0][2] == board[1][1] == board[2][0]):
                return "F" if last_move.by_first_player else "S"

        if self.move_set.count() >= 9:
            return "D"
        return "A"

    def toogle_next_player(self):
        if self.next_to_move == self.first_player:
            self.next_to_move = self.second_player
        else:
            self.next_to_move = self.first_player


    def is_empty(self, x, y):
        return not self.move_set.filter(x=x, y=y).exists()

    def last_move(self):
        return self.move_set.latest()

    def get_absolute_url(self):
        # This does basically the same as URL tag.. construct reversly mapping URL, use it with Reverse
        return reverse('tictactoe_game_detail', args=[self.id])

    def is_users_move(self, user):
        return self.status == 'A' and self.next_to_move == user

    def __str__(self):
        return "{0}. {1} vs {2}".format(self.id, self.first_player, self.second_player)

# Create your models here.
class Move(models.Model):
    x = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(BOARD_SIZE-1)])
    y = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(BOARD_SIZE-1)])
    comment = models.CharField(max_length=300)
    game = models.ForeignKey(Game)
    by_first_player = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # this is set for django so it know it can use .latest()
        # other build in features
        get_latest_by = 'timestamp'

    def player(self):
        return self.game.first_player if self.by_first_player else self.game.second_player

class Invitation(models.Model):
    from_user = models.ForeignKey(User, related_name="invitations_sent")
    to_user = models.ForeignKey(User, related_name="invitations_received", verbose_name="User to invite", help_text="Please select the user you want to play with")
    message = models.CharField("Optional Message", max_length=300, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
