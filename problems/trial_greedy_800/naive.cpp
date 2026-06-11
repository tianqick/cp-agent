#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>
using namespace std;

// 暴力解法：枚举所有可能的目标递增序列
// 但由于值域太大，我们用贪心验证的方式
// 这里用另一种贪心思路来验证：每次让当前元素至少比前一个大1
int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<long long> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    // 暴力解法：从左到右，保证每个元素严格大于前一个
    // 这其实就是贪心解法，因为只能增加，所以贪心是最优的
    long long ans = 0;
    long long prev = 0; // 前一个元素的值
    
    for (int i = 0; i < n; i++) {
        if (a[i] <= prev) {
            // 需要增加到 prev + 1
            ans += (prev + 1 - a[i]);
            prev = prev + 1;
        } else {
            prev = a[i];
        }
    }
    
    cout << ans << endl;
    
    return 0;
}
