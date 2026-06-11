#include <iostream>
#include <vector>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<long long> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    long long ans = 0;
    long long need = 0; // 当前元素至少需要是 need
    
    for (int i = 0; i < n; i++) {
        if (a[i] <= need) {
            // 需要将 a[i] 增加到 need + 1
            ans += (need + 1 - a[i]);
            need = need + 1;
        } else {
            // a[i] 已经大于 need，不需要操作
            need = a[i];
        }
    }
    
    cout << ans << endl;
    
    return 0;
}
