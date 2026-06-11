# Positive Segment Partition

**Time limit:** 1 second  
**Memory limit:** 256 MB

## Problem Statement

You are given an array $a$ of $n$ integers (possibly negative). You need to partition the array into **several contiguous non-empty segments**. The partition must cover the entire array — every element belongs to exactly one segment.

For each segment, define its **score** as follows:
- If the sum of elements in the segment is **strictly greater than 0**, the score equals that sum.
- Otherwise, the score is $0$.

The **total score** of a partition is the sum of scores of all its segments.

Your task is to find the **maximum possible total score** you can achieve by optimally partitioning the array.

## Input

- The first line contains a single integer $n$ $(1 \le n \le 2 \cdot 10^5)$ — the length of the array.
- The second line contains $n$ integers $a_1, a_2, \dots, a_n$ $(-10^9 \le a_i \le 10^9)$ — the elements of the array.

## Output

Output a single integer — the maximum possible total score.

## Examples

### Example 1
```
Input:
5
3 -2 1 4 -1

Output:
6
```
**Explanation:** Partition as $[3, -2, 1, 4]$ (sum $= 6 > 0$, score $= 6$) and $[-1]$ (sum $= -1 \le 0$, score $= 0$). Total score $= 6$.

### Example 2
```
Input:
3
-1 -2 -3

Output:
0
```
**Explanation:** All elements are negative. Any segment has sum $\le 0$, so every segment scores $0$. Maximum total score is $0$.

### Example 3
```
Input:
4
1 2 3 4

Output:
10
```
**Explanation:** Take the whole array as one segment. Sum $= 10 > 0$, score $= 10$.

### Example 4
```
Input:
6
-3 5 -2 1 -4 6

Output:
9
```
**Explanation:** Optimal partition: $[-3, 5]$ (sum $= 2$, score $= 2$), $[-2, 1, -4, 6]$ (sum $= 1$, score $= 1$)... wait, let's compute properly.  
Partition $[-3, 5, -2]$ (sum $= 0$, score $= 0$), $[1]$ (sum $= 1$, score $= 1$), $[-4, 6]$ (sum $= 2$, score $= 2$) → total $= 3$.  
Better: $[-3, 5]$ (score $= 2$), $[-2, 1, -4, 6]$ (score $= 1$) → total $= 3$.  
Best: $[5]$ (score $= 5$), $[-3, -2, 1, -4, 6]$ (sum $= -2$, score $= 0$) → $5$? No.  
Actually best is $[-3, 5, -2, 1, -4, 6]$ (sum $= 3$, score $= 3$) or just $[5, -2, 1, -4, 6]$ (sum $= 6$, score $= 6$)... Let's check: $5-2+1-4+6 = 6$. Plus $[-3]$ scores 0. Total $= 6$.  
The optimal is: $[-3]$ (0), $[5, -2, 1]$ (4), $[-4, 6]$ (2) → total $= 6$. Or $[-3]$ (0), $[5, -2, 1, -4, 6]$ (6) → total $= 6$.

## Constraints

- $1 \le n \le 2 \cdot 10^5$
- $-10^9 \le a_i \le 10^9$
- The answer fits in a 64-bit signed integer.
