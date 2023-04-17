def test_cpv_algorithms(cpv_processor, fake_cpv, real_cpv, problematic_cpv):
    assert cpv_processor.cpv_exists(cpv_code=fake_cpv) is False
    assert cpv_processor.cpv_exists(cpv_code=real_cpv)
    assert cpv_processor.cpv_exists(cpv_code=problematic_cpv)

    assert cpv_processor.get_cpv_rank(cpv_code=real_cpv) == 4
    assert cpv_processor.get_cpv_rank(cpv_code=problematic_cpv) == 3
    assert cpv_processor.get_cpv_rank(cpv_code=fake_cpv) is None

    assert cpv_processor.get_cpv_rank_code(cpv_code=real_cpv, rank=0) == '63000000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=problematic_cpv, rank=0) == '60000000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=fake_cpv, rank=0) is None

    assert cpv_processor.get_cpv_rank_code(cpv_code=real_cpv, rank=1) == '63700000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=problematic_cpv, rank=1) == '60100000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=fake_cpv, rank=1) is None

    assert cpv_processor.get_cpv_rank_code(cpv_code=real_cpv, rank=2) == '63710000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=problematic_cpv, rank=2) == '60100000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=fake_cpv, rank=2) is None

    assert cpv_processor.get_cpv_rank_code(cpv_code=real_cpv, rank=3) == '63712000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=problematic_cpv, rank=3) == '60112000'
    assert cpv_processor.get_cpv_rank_code(cpv_code=fake_cpv, rank=3) is None

    assert cpv_processor.get_cpv_rank_code(cpv_code=real_cpv, rank=4) == real_cpv
    assert cpv_processor.get_cpv_rank_code(cpv_code=problematic_cpv, rank=4) is None
    assert cpv_processor.get_cpv_rank_code(cpv_code=fake_cpv, rank=4) is None

    assert cpv_processor.get_cpv_rank_code(cpv_code=real_cpv, rank=5) is None
    assert cpv_processor.get_cpv_rank_code(cpv_code=problematic_cpv, rank=5) is None
    assert cpv_processor.get_cpv_rank_code(cpv_code=fake_cpv, rank=5) is None

    assert cpv_processor.get_cpv_rank_list(cpv_codes=[real_cpv, fake_cpv, problematic_cpv]) == [4, None, 3]
    assert cpv_processor.get_cpv_parent_list(cpv_codes=[real_cpv, fake_cpv, problematic_cpv]) == ['63712000',
                                                                                                  '60100000']
    assert cpv_processor.get_cpv_rank_code_list(cpv_codes=[real_cpv, fake_cpv, problematic_cpv], rank=0) == [
        '63000000',
        '60000000']

    assert cpv_processor._get_cpv_parent(cpv_code='10000000') is None
    assert cpv_processor.get_cpv_rank(None) is None
    assert cpv_processor.get_cpv_rank_code_list(None, rank=0) is None
    assert cpv_processor.get_cpv_rank_list(None) is None
    assert cpv_processor.get_cpv_parent_list(None) is None
