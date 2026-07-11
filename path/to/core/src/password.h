#ifndef PASSWORD_H
#define PASSWORD_H

#include <stdint.h>

// Function to generate a secure random salt
uint8_t* generate_salt(size_t salt_length);

// Function to verify a password
int verify_password(const uint8_t* password, size_t password_length, const uint8_t* salt, size_t salt_length);

// Function to check if a password is correct
int check_password(const uint8_t* password, size_t password_length, const uint8_t* salt, size_t salt_length);

#endif  // PASSWORD_H