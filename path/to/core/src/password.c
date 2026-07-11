#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include <sys/random.h>

// Function to generate a secure random salt
uint8_t* generate_salt(size_t salt_length) {
    uint8_t* salt = malloc(salt_length);
    if (!salt) {
        fprintf(stderr, "Memory allocation failed\n");
        exit(1);
    }

    // Use /dev/urandom for secure random number generation
    if (getrandom(salt, salt_length, GRND_RANDOM) != 0) {
        fprintf(stderr, "Failed to generate random salt\n");
        free(salt);
        exit(1);
    }

    return salt;
}

// Function to verify a password
int verify_password(const uint8_t* password, size_t password_length, const uint8_t* salt, size_t salt_length) {
    if (!password || !salt) {
        return 0; // Password or salt is null
    }

    if (password_length > salt_length) {
        return 0; // Password is longer than salt
    }

    // Use SHA-256 for secure password verification
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_CTX sha256;
    SHA256_Init(&sha256);
    for (size_t i = 0; i < password_length; i++) {
        SHA256_Update(&sha256, salt, salt_length);
        SHA256_Update(&sha256, password, password_length);
        SHA256_Final(hash, &sha256);
    }

    // Check if the password is correct
    for (size_t i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        if (hash[i] != salt[i]) {
            return 0; // Password is incorrect
        }
    }

    return 1; // Password is correct
}

// Function to check if a password is correct
int check_password(const uint8_t* password, size_t password_length, const uint8_t* salt, size_t salt_length) {
    // Generate a new salt for each password check
    uint8_t* new_salt = generate_salt(salt_length);
    if (!new_salt) {
        return 0; // Memory allocation failed
    }

    // Verify the password using the new salt
    int result = verify_password(password, password_length, new_salt, salt_length);
    free(new_salt);
    return result;
}