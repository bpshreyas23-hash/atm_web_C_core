#include <stddef.h>

int verify_pin(int pin, int entered_pin) { return pin == entered_pin; }

int deposit_money(double *balance, double amount) {
    if (balance == NULL || amount <= 0.0) return 0;
    *balance += amount;
    return 1;
}

int withdraw_money(double *balance, double amount) {
    if (balance == NULL || amount <= 0.0 || amount > *balance) return 0;
    *balance -= amount;
    return 1;
}

int change_pin(int *pin, int old_pin, int new_pin, int confirm_pin) {
    if (pin == NULL || old_pin != *pin) return 0;
    if (new_pin < 1000 || new_pin > 9999) return 0;
    if (new_pin != confirm_pin) return 0;
    *pin = new_pin;
    return 1;
}
