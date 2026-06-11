#include <iostream>
#include <cstdlib>
#include <random>
#include <algorithm>
#include <set>
using namespace std;

int main(int argc, char* argv[]) {
    int test_id = atoi(argv[1]);
    int total_tests = atoi(argv[2]);
    
    mt19937 rng(test_id * 12345 + 67890);
    
    int n, k;
    long long max_val;
    
    if (test_id == 1) {
        // 样例1: 小数据
        n = 5; k = 2;
        cout << n << " " << k << "\n";
        cout << "3 1 4 1 5\n";
        return 0;
    }
    if (test_id == 2) {
        // 样例2: k=0，所有元素相同
        n = 4; k = 0;
        cout << n << " " << k << "\n";
        cout << "5 5 5 5\n";
        return 0;
    }
    if (test_id == 3) {
        // n=1 边界
        n = 1; k = 0;
        cout << n << " " << k << "\n";
        cout << "42\n";
        return 0;
    }
    if (test_id == 4) {
        // n=1, k很大
        n = 1; k = 1000000000;
        cout << n << " " << k << "\n";
        cout << "1\n";
        return 0;
    }
    
    // 根据test_id选择不同类型的测试
    if (test_id <= 8) {
        // 小数据 n <= 20
        n = uniform_int_distribution<int>(2, 20)(rng);
        k = uniform_int_distribution<int>(0, 20)(rng);
    } else if (test_id <= 12) {
        // 中等数据 n <= 500
        n = uniform_int_distribution<int>(20, 500)(rng);
        k = uniform_int_distribution<int>(0, 1000)(rng);
    } else if (test_id <= 16) {
        // 较大数据 n <= 5000
        n = uniform_int_distribution<int>(500, 5000)(rng);
        k = uniform_int_distribution<int>(0, 100000)(rng);
    } else if (test_id == 17) {
        // k = 0，所有元素可以相同也可以不同
        n = uniform_int_distribution<int>(100, 200000)(rng);
        k = 0;
    } else if (test_id == 18) {
        // k 很大，几乎无限制
        n = uniform_int_distribution<int>(100, 200000)(rng);
        k = 1000000000;
    } else if (test_id == 19) {
        // 所有元素相同，k=0
        n = uniform_int_distribution<int>(100, 200000)(rng);
        k = 0;
    } else if (test_id == 20) {
        // 严格递增序列，k很小
        n = uniform_int_distribution<int>(100, 200000)(rng);
        k = uniform_int_distribution<int>(0, 2)(rng);
    } else if (test_id == 21) {
        // n=200000 最大数据
        n = 200000;
        k = uniform_int_distribution<int>(0, 1000000)(rng);
    } else if (test_id == 22) {
        // 最大数据，k=0
        n = 200000;
        k = 0;
    } else if (test_id == 23) {
        // 最大数据，k=10^9
        n = 200000;
        k = 1000000000;
    } else if (test_id == 24) {
        // 大值范围，中等n
        n = uniform_int_distribution<int>(1000, 50000)(rng);
        k = uniform_int_distribution<int>(0, 1000000000)(rng);
    } else if (test_id == 25) {
        // 只有两种值
        n = uniform_int_distribution<int>(100, 200000)(rng);
        k = uniform_int_distribution<int>(0, 5)(rng);
    } else if (test_id == 26) {
        // 先递增后递减
        n = uniform_int_distribution<int>(100, 200000)(rng);
        k = uniform_int_distribution<int>(1, 100)(rng);
    } else if (test_id == 27) {
        // k=1，值域小
        n = uniform_int_distribution<int>(1000, 200000)(rng);
        k = 1;
    } else if (test_id == 28) {
        // 随机大数据
        n = uniform_int_distribution<int>(100000, 200000)(rng);
        k = uniform_int_distribution<int>(0, 1000000000)(rng);
    } else if (test_id == 29) {
        // 小值域
        n = uniform_int_distribution<int>(100000, 200000)(rng);
        k = uniform_int_distribution<int>(0, 10)(rng);
    } else {
        // 随机数据
        n = uniform_int_distribution<int>(50000, 200000)(rng);
        k = uniform_int_distribution<int>(0, 1000000000)(rng);
    }
    
    cout << n << " " << k << "\n";
    
    // 根据 test_id 选择不同的值域
    max_val = 1000000000LL;
    if (test_id == 25) max_val = 5; // 只有两种值
    if (test_id == 29) max_val = 10; // 小值域
    if (test_id == 27) max_val = 100; // k=1时小值域
    
    if (test_id == 19) {
        // 所有元素相同
        int val = uniform_int_distribution<int>(1, 1000000000)(rng);
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << " ";
            cout << val;
        }
    } else if (test_id == 20) {
        // 严格递增
        long long cur = 1;
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << " ";
            cout << cur;
            cur += uniform_int_distribution<long long>(1, (long long)k + 1)(rng);
            if (cur > 1000000000LL) cur = 1000000000LL;
        }
    } else if (test_id == 26) {
        // 先递增后递减
        int mid = n / 2;
        long long cur = 1;
        for (int i = 0; i < mid; i++) {
            if (i > 0) cout << " ";
            cout << cur;
            cur += (long long)uniform_int_distribution<int>(1, 3)(rng);
            if (cur > 1000000000) cur = 1000000000;
        }
        for (int i = mid; i < n; i++) {
            cout << " " << cur;
            cur -= (long long)uniform_int_distribution<int>(1, 3)(rng);
            if (cur < 1) cur = 1;
        }
    } else {
        // 随机数据
        for (int i = 0; i < n; i++) {
            if (i > 0) cout << " ";
            cout << uniform_int_distribution<long long>(1, max_val)(rng);
        }
    }
    cout << "\n";
    
    return 0;
}