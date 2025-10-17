import random

# rand_list =
rand_list = [random.randint(1, 2) for x in range(10)]

# list_comprehension_below_10 =
below_10_comprehension = [num for num in rand_list if num < 10]

# list_comprehension_below_10 =
below_10_filter = list(filter(lambda x: x < 10, rand_list))
