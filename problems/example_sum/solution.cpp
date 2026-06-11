// Solution: Sum of Array
// Complexity: O(n) time, O(1) space
#include <iostream>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    long long sum = 0;  // use long long to avoid overflow
    for (int i = 0; i < n; i++) {
        int x;
        cin >> x;
        sum += x;
    }

    cout << sum << "\n";
    return 0;
}
