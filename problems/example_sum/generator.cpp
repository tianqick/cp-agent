// Generator for "Sum of Array" — testlib-based
#include "testlib.h"
#include <iostream>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);

    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);

    int n;
    if (idx <= 2) {
        // Edge cases
        n = (idx == 1) ? 1 : 10;
    } else if (idx <= total / 3) {
        n = rnd.next(1, 100);
    } else if (idx <= total * 2 / 3) {
        n = rnd.next(100, 10000);
    } else {
        n = rnd.next(10000, 100000);
    }

    cout << n << endl;
    for (int i = 0; i < n; i++) {
        cout << rnd.next(1, 1000000);
        if (i + 1 < n) cout << " ";
    }
    cout << endl;

    return 0;
}
