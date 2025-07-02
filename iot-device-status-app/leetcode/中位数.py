def get_median(arr1, arr2):
    '''

    :param arr1:
    :param arr2:
    主要思路是利用二分法，设定数组arr1和arr2,长度分别是m,n。总长度是lenth
        1.首先是对两个数组取最小长度，交互数组，并且长度大于2
        2.取到最短长度后，将长度除以2，并且将数组分成左右两部分，总数是偶数情况下，左半部分保证的数量和=右半部分的数量和
        3.其实一直让左边arr1数组下标值m_idx进行二分法就可以了，并保证左边数组arr2的 n_idx = half-m_idx，并且保证左部分最大值<右部分的最小值
        4.特殊情况：
            a.假设arr1的最小下标对应的值大于arr2最大下标的值,若为奇数，中位数 median = arr2[(lenth+1)//2] ,偶数则为 median = (arr2[lenth//2]+arr2[(lenth//2)-1])/2.0
            b.同理，假设arr2的最小下标值大于arr1的最大下标的值，若为奇数，中位数 median = arr2[(lenth+1)//2-m],偶数则为 median = (arr2[(lenth+1)//2-m]+arr2[(lenth+1)//2-m-1])/2.0
    :return:
    '''

    if len(arr1) > len(arr2):
        arr1, arr2 = arr2, arr1
    m = len(arr1)
    n = len(arr2)
    lenth = m + n
    left, right, half = 0, m, (lenth + 1) // 2
    while left <= right:
        m_idx = (left + right) // 2
        n_idx = half - m_idx
        if m_idx < m and arr1[m_idx] < arr2[n_idx - 1]:
            left += 1
            # left = m_idx + 1
        elif m_idx > 0 and arr1[m_idx - 1] > arr2[m_idx]:
            right -= 1
            # right = m_idx - 1
        else:
            if m_idx == 0:
                max_left_val = arr2[n_idx - 1]
            elif n_idx == 0:
                max_left_val = arr1[m_idx - 1]
            else:
                max_left_val = max(arr1[m_idx - 1], arr2[n_idx - 1])
            if (m + n) % 2 == 1:
                return max_left_val
            if m_idx == m:
                min_right_val = arr2[n_idx]
            elif n_idx == n:
                min_right_val = arr1[m_idx]
            else:
                min_right_val = min(arr2[n_idx], arr1[m_idx])
            return (min_right_val + max_left_val) / 2

