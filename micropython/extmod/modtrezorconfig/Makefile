NAME=norcow_test
CC=gcc
CFLAGS=-Wall -Wextra -Werror -DUNIX
LDFLAGS=
LIBS=
OBJ=$(NAME).o norcow.o

$(NAME): $(OBJ)
	$(CC) $(LDFLAGS) $(LIBS) $(OBJ) -o $(NAME)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(NAME) $(OBJ)
