#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    long long d;
    cin >> n >> k >> d;
    
    vector<long long> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    sort(a.begin(), a.end());
    
    int groups = 0;
    int i = 0;
    while (i < n) {
        groups++;
        long long first = a[i];
        int count = 0;
        while (i < n && count < k && a[i] - first <= d) {
            i++;
            count++;
        }
    }
    
    cout << groups << endl;
    
    return 0;
}
