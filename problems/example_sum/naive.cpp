// Naive solution for "Sum of Array" (same logic, for stress test verification)
// Complexity: O(n) time, O(1) space
#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;

    long long sum = 0;
    for (int i = 0; i < n; i++) {
        int x;
        cin >> x;
        sum += x;
    }

    cout << sum << "\n";
    return 0;
}
