PosixPath('/home/raghuram/Documents/2023USATaxes/zerodha_console_account_values.json')

b7ac49463cffd04e4c73d21252cafc1e

10110111101011000100100101000110
00111100111111111101000001001110
01001100011100111101001000010010
01010010110010101111110000011110

```
0xb7ac49463cffd04e4c73d21252cafc1e
0b10110111101011000100100101000110001111001111111111010000010011100100110001110011110100100001001001010010110010101111110000011110
b'10110111101011000100100101000110001111001111111111010000010011100100110001110011110100100001001001010010110010101111110000011110'

bytearray.fromhex("b7ac49463cffd04e4c73d21252cafc1e")
[bin(i) for i in bytearray.fromhex("b7ac49463cffd04e4c73d21252cafc1e")]
[f"{i:b}" for i in bytearray.fromhex("b7ac49463cffd04e4c73d21252cafc1e")]
hash_ = "".join([f"{i:08b}" for i in bytearray.fromhex("b7ac49463cffd04e4c73d21252cafc1e")])

hash_[0:64]
hash_[64:96]
hash_[96:128]
```




HEX Color Codes: FF5733
111111110101011100110011


My MD5 Hashes are 128 bits
HEX Color Codes are 24 bits

hash_ = "".join([f"{i:08b}" for i in bytearray.fromhex("b7ac49463cffd04e4c73d21252cafc1e")])
hash_ = 0xb7ac49463cffd04e4c73d21252cafc1e
l = 100*hash_[0:64]/2**64
a = -125 + 250*(hash_[64:96]/2**32)
b = -125 + 250*(hash_[96:128]/2**32)




import colorsys

29744ebbd2341eb3ffc81fddb7020f07
29744ebbd2341eb3 ffc81fddb7020f07
hash_ = bytearray.fromhex("29744ebbd2341eb3ffc81fddb7020f07")
hash_ = "".join([f"{i:08b}" for i in hash_])
l = 100 * int(hash_[0:64],base=2) / 2**64
a = -125 + 250 * (int(hash_[64:96],base=2)/2**32)
b = -125 + 250 * (int(hash_[96:128],base=2)/2**32)


# hsl(360 100% 50%)
h = 360 * (int(hash_[0:64],base=2)/2**64)
s = 100 * (int(hash_[64:96],base=2)/2**32)
l = 100 * (int(hash_[96:128],base=2)/2**32)

colorsys.hls_to_rgb(h, l, s)
[255*i for i in colorsys.hls_to_rgb(h, l, s)]

"rgb(" + ",".join([str(int(255*i)) for i in colorsys.hls_to_rgb(h, l, s)]) + ")"


```python
import colorsys
def colorhash(hash_: string) -> string:
    hash_ = bytearray.fromhex(hash_)
    hash_ = "".join([f"{i:08b}" for i in hash_])
    h = int(hash_[0:64],base=2)/2**64
    s = int(hash_[64:96],base=2)/2**32
    l = int(hash_[96:128],base=2)/2**32
    return "rgb(" + ",".join([str(int(255*i)) for i in colorsys.hls_to_rgb(h, l, s)]) + ")"
```