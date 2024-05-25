import secrets
from math import gcd, sqrt
import random
import gmpy2

from utils import generate_two_large_distinct_primes

# rigth RSA size
# RSA_KEY_SIZE = 3072  # RSA key size for 128 bits of security (modulus size)
RSA_KEY_SIZE = 1000
RSA_PRIME_SIZE = int(RSA_KEY_SIZE / 2)
ACCUMULATED_PRIME_SIZE = 128  # taken from: LLX, "Universal accumulators with efficient nonmembership proofs", construction 1

# #my is_prime
# def is_prime(n):
#     """Check if a number is prime using integer arithmetic."""
#     if n <= 1:
#         return False
#     if n <= 3:
#         return True  # 2 and 3 are primes
#     if n % 2 == 0 or n % 3 == 0:
#         return False  # Exclude multiples of 2 and 3 quickly
#     i = 5
#     while i * i <= n:  # i * i is the same as sqrt(n) but avoids floating-point operations
#         if n % i == 0 or n % (i + 2) == 0:
#             return False
#         i += 6
#     return True

def rabin_miller(num):
    # Returns True if num is a prime number.

    s = num - 1
    t = 0
    while s % 2 == 0:
        # keep halving s while it is even (and use t
        # to count how many times we halve s)
        s = s // 2
        t += 1

    for trials in range(5): # try to falsify num's primality 5 times
        a = random.randrange(2, num - 1)
        v = pow(a, s, num)
        if v != 1: # this test does not apply if v is 1.
            i = 0
            while v != (num - 1):
                if i == t - 1:
                    return False
                else:
                    i = i + 1
                    v = (v ** 2) % num
    return True


def is_prime(num):
    # Return True if num is a prime number. This function does a quicker
    # prime number check before calling rabin_miller().

    if (num < 2):
        return False # 0, 1, and negative numbers are not prime

    # About 1/3 of the time we can quickly determine if num is not prime
    # by dividing by the first few dozen prime numbers. This is quicker
    # than rabin_miller(), but unlike rabin_miller() is not guaranteed to
    # prove that a number is prime.
    lowPrimes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997]

    if num in lowPrimes:
        return True

    # See if any of the low prime numbers can divide num
    for prime in lowPrimes:
        if (num % prime == 0):
            return False

    # If all else fails, call rabin_miller() to determine if num is a prime.
    return rabin_miller(num)


def generate_large_prime(n,phi):
    while True:
        #my version
        num = random_coprime_with_totient(n, phi)
        # num = secrets.randbelow(pow(2, num_of_bits))
        if is_prime(num):
            return num

def setup():
    # draw strong primes p,q
    p, q = generate_two_large_distinct_primes(RSA_PRIME_SIZE)
    n = p*q
    # draw random number within range of [0,n-1]
    A0 = secrets.randbelow(n)
    return n, A0, dict()

def n_for_RSA():
    p, q = generate_two_large_distinct_primes(RSA_PRIME_SIZE)
    n = p*q
    phi = (p-1)*(q-1)
    return n, phi

def random_coprime_with_totient(n, phi):
    while True:
        rand_num = random.randint(2, n-1)  # Start from 2 since 1 is not prime.
        if gcd(rand_num, phi) == 1 and is_prime(rand_num):
            return rand_num

def rsa_accumulate(n, tokenID, A):
    """
    Accumulates a tokenID into the RSA accumulator.

    :param g: The base of the accumulator.
    :param n: The modulus, product of two large primes p and q.
    :param tokenID: The token ID to accumulate, must be coprime with the totient of n.
    :param current_accumulator: The current value of the accumulator.
    :return: The new value of the accumulator after including the tokenID.
    """
    # Accumulate the tokenID
    if A == 0:
        A = 2
    else:
        A = pow(A, tokenID, n)
    return A


def root_extraction(a_value, tokenID, n_value, phi):
# Example values (replace with your actual values)
    A = gmpy2.mpz(a_value)
    n = gmpy2.mpz(n_value)  # Convert n_value to gmpy2.mpz object if not already done
    phi = gmpy2.mpz(phi)  # Convert n_value to gmpy2.mpz object if not already done

    # e_j = gmpy2.mpz(tokenID, 16)  # Element or exponent value
    e_j = gmpy2.mpz(tokenID)
    # Compute the modular root if e_j is coprime to n
    if gmpy2.gcd(e_j, phi) == 1:
        inverse_ej = gmpy2.invert(e_j, phi)
        new_accumulator = gmpy2.powmod(A, inverse_ej, n)
        return new_accumulator
    else:
        print("e_j is not coprime to phi(n), computation not feasible")


def verification_token(A, tokenID_verify, n):
    base = root_extraction(A, tokenID_verify, n)
    verified = pow(base, tokenID_verify, n)
    return verified



