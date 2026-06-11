// Generator template — testlib-based
// Usage: ./generator <test_index> <total_tests>
#include "testlib.h"
#include <iostream>
#include <vector>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);

    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);

    // Adaptive sizing based on test index
    int n;
    if (idx <= 2) {
        n = rnd.next(1, 10);           // small edge cases
    } else if (idx <= total / 3) {
        n = rnd.next(10, 100);          // medium
    } else if (idx <= total * 2 / 3) {
        n = rnd.next(100, 1000);        // large
    } else {
        n = rnd.next(1000, 10000);      // stress / max
    }

    cout << n << endl;
    for (int i = 0; i < n; i++) {
        cout << rnd.next(1, 1000000);
        if (i + 1 < n) cout << " ";
    }
    cout << endl;

    return 0;
}
