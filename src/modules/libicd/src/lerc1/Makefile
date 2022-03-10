
C_SRC = Lerc1Image.c

CXXFLAGS = -O2 -fPIC $(DEBUG)

OBJECTS = $(C_SRC:.c=.o)

TARGET = $(OBJECTS)

default : $(TARGET)

%.o	:	%.c
	$(CC) $(CXXFLAGS) $(DEFINES) -c $< -o $@

clean	:
	$(RM) $(TARGET)
