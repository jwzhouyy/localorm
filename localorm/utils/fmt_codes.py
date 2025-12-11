from dataclasses import dataclass

DATA = '''
Emma
Olivia
Ava
Sophia
Mia
Isabella
Amelia
Harper
Evelyn
Charlotte
'''


@dataclass
class Result:
    map_data: dict
    set_data: set

    def __repr__(self):
        return f'map_data={self.map_data}\nset_data={self.set_data}'


def fmt_m_c(d, split=''):
    sd = []
    sds = []
    s_set = set()
    map_data = {}
    for s in d.split('\n'):
        s = s.strip()
        # s = s.split('/')[-1]
        if s:
            s_set.add(s)
            c_s = []
            c_s_s = set()
            for i, c in enumerate(s.split(split), 1):
                c = c.strip() or ''
                # if c:
                c_s.append(c)
                c_s_s.add(c)

            if len(c_s) >= 2:
                map_data[c_s[0]] = c_s[1]
            # c_s.append('无')
            sd.append(c_s)
            sds.append(c_s_s)
    # print(sd)
    # print(map_data)

    # print(s_set)
    s_list = [s[0] for s in sd]
    # print(s_list)

    # for _sd in sd:
    #     print('@'.join(_sd))

    # result = {s_list[i]: s_list[i + 1] for i in range(0, len(s_list), 2)}
    # print(result)
    result = Result(map_data=map_data, set_data=s_set)
    return result


def main():
    result = fmt_m_c(DATA, '\n')
    print(result)


if __name__ == '__main__':
    main()
