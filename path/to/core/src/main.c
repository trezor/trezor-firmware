#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "password.h"

int main() {
    // Generate a random salt
    uint8_t* salt = generate_salt(32);
    if (!salt) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }

    // Set the password
    const uint8_t password[] = "mysecretpassword";
    size_t password_length = strlen((char*)password);

    // Check if the password is correct
    int result = check_password(password, password_length, salt, 32);
    if (result) {
        printf("Password is correct\n");
    } else {
        printf("Password is incorrect\n");
    }

    free(salt);
    return 0;
}