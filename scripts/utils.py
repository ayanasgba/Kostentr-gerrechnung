def format_de(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return str(value)

    if value.is_integer():
        return f"{int(value):n}".replace(",", ".")
    else:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
