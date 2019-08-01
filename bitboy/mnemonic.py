from m5stack import LCD, fonts, color565
from bitcoin.mnemonic import secure_mnemonic

lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()


def seed_rng():
    from urandom import seed
    seed(888)

def title(s):
    # calculations
    sw = fonts.tt32.get_width(s)
    padding = (lcd.width - sw) // 2

    # configure lcd
    lcd.set_font(fonts.tt32)
    lcd.set_pos(padding, 20)

    # print
    lcd.print(s)


def mnemonic_columns():
    # generate mnemonic
    mnemonic = secure_mnemonic()

    # print title
    title("Seed Words")

    # set font
    lcd.set_font(fonts.tt24)

    # variables for printing
    words = mnemonic.split()
    labeled = [str(i) + ". " + word for i, word in enumerate(words, 1)]
    words_per_col = len(words) // 2
    col_width = max([lcd._font.get_width(w) for w in labeled])
    # 2 colunms with equal spacing on all sides
    pad_x = (lcd.width - 2 * col_width) // 3
    pad_y = 20
    left_col_x, left_col_y = pad_x, lcd._y + pad_y
    right_col_x, right_col_y = 2 * pad_x + col_width, lcd._y + pad_y

    # print left column
    print(left_col_x, left_col_y)
    lcd.set_pos(left_col_x, left_col_y)
    for word in labeled[:words_per_col]:
        lcd.print(word)

    # print right column
    print(right_col_x, right_col_y)
    lcd.set_pos(right_col_x, right_col_y)
    for word in labeled[words_per_col:]:
        lcd.print(word)


if __name__ == '__main__':
    seed_rng()
    mnemonic_columns()
