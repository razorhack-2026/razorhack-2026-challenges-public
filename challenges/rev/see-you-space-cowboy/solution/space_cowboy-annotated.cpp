#include <iostream>
#include <typeinfo> // Required for typeid
#include <cxxabi.h>
#include <cstdint>

// Least-Significant Bit -> Most-Significant Bit, i.e. Little-Endian
// Always Unsigned
struct BitO {};
struct BitZ {};

template<typename... Xs>
struct List {};

using Bin0 = List<BitZ>;
using Bin1 = List<BitO>;
using Bin2 = List<BitZ, BitO>;
using Bin3 = List<BitO, BitO>;
using Bin4 = List<BitZ, BitZ, BitO>;
using Bin5 = List<BitO, BitZ, BitO>;
using Bin6 = List<BitZ, BitO, BitO>;
using Bin7 = List<BitO, BitO, BitO>;
using Bin8 = List<BitZ, BitZ, BitZ, BitO>;
using Bin9 = List<BitO, BitZ, BitZ, BitO>;
using BinA = List<BitZ, BitO, BitZ, BitO>;
using BinB = List<BitO, BitO, BitZ, BitO>;
using BinC = List<BitZ, BitZ, BitO, BitO>;
using BinD = List<BitO, BitZ, BitO, BitO>;
using BinE = List<BitZ, BitO, BitO, BitO>;
using BinF = List<BitO, BitO, BitO, BitO>;

template<typename L>
struct ToInt {};

template<typename... Bits>
struct ToInt<List<BitO, Bits...>> {
    static constexpr std::uint64_t res = (ToInt<List<Bits...>>::res << 1) | 1;
};

template<typename... Bits>
struct ToInt<List<BitZ, Bits...>> {
    static constexpr std::uint64_t res = (ToInt<List<Bits...>>::res << 1) | 0;
};

template<>
struct ToInt<Bin0> {
    static constexpr std::uint64_t res = 0;
};

template<>
struct ToInt<Bin1> {
    static constexpr std::uint64_t res = 1;
};



template<typename CondBit, typename A, typename B>
struct IfThenElse {};

template<typename A, typename B> struct IfThenElse<BitZ, A, B> { using res = B; };
template<typename A, typename B> struct IfThenElse<BitO, A, B> { using res = A; };




template<typename ListA, typename ListB>
struct Concat {};

template<typename... AXs, typename... BXs>
struct Concat<List<AXs...>, List<BXs...>> {
    using res = List<AXs..., BXs...>;
};



template<typename L>
struct Head {};

template<typename X, typename... Xs>
struct Head<List<X, Xs...>> {
    using res = X;
};



template<typename L>
struct Last {};

template<typename X, typename... Xs>
struct Last<List<X, Xs...>> {
    using res = typename Last<List<Xs...>>::res;
};

template<typename X>
struct Last<List<X>> {
    using res = X;
};



template<typename L>
struct Tail {};

template<typename X, typename... Xs>
struct Tail<List<X, Xs...>> {
    using res = List<Xs...>;
};

template<typename X>
struct Tail<List<X>> {
    using res = List<>;
};

template<>
struct Tail<List<>> {
    using res = List<>;
};



template<typename L>
struct Init {};

template<typename X, typename... Xs>
struct Init<List<X, Xs...>> {
    using res = typename Concat<
        List<X>,
        typename Init<List<Xs...>>::res
    >::res;
};

template<typename X>
struct Init<List<X>> {
    using res = List<>;
};

template<>
struct Init<List<>> {
    using res = List<>;
};



template<typename L>
struct Rev {};

template<typename X, typename... Xs>
struct Rev<List<X, Xs...>> {
    using res = typename Concat<
        typename Rev<List<Xs...>>::res,
        List<X>
    >::res;
};

template<>
struct Rev<List<>> {
    using res = List<>;
};



template<typename L>
struct RemoveLeadingZero {};

template<typename... Xs>
struct RemoveLeadingZero<List<BitZ, Xs...>> {
    using res = typename RemoveLeadingZero<List<Xs...>>::res;
};

template<typename... Xs>
struct RemoveLeadingZero<List<BitO, Xs...>> {
    using res = List<BitO, Xs...>;
};

template<>
struct RemoveLeadingZero<List<BitZ>> {
    using res = List<BitZ>;
};

template<>
struct RemoveLeadingZero<List<>> {
    using res = List<>;
};



template<typename L>
struct RemoveTrailingZero {
    using res = typename Rev<typename RemoveLeadingZero<typename Rev<L>::res>::res>::res;
};



/* ------ Bitwise Not ------ */
template<typename Bin>
struct BitwiseNot {
    using res = typename Concat<
        typename IfThenElse<typename Head<Bin>::res, Bin0, Bin1>::res,
        typename BitwiseNot<
            typename Tail<Bin>::res
        >::res
    >::res;
};

template<>
struct BitwiseNot<List<>> {
    using res = List<>;
};
/* ------ Bitwise Not ------ */



/* ------ Bitwise And ------ */
template<typename BitA, typename BitB>
struct AndOp {};
template<> struct AndOp<BitZ, BitZ> { using res = BitZ; };
template<> struct AndOp<BitZ, BitO> { using res = BitZ; };
template<> struct AndOp<BitO, BitZ> { using res = BitZ; };
template<> struct AndOp<BitO, BitO> { using res = BitO; };

template<typename BinA, typename BinB>
struct BitwiseAnd {
private:
    using op = AndOp<typename Head<BinA>::res, typename Head<BinB>::res>;
public:
    using res = typename Concat<
        typename IfThenElse<typename Head<BinA>::res, List<typename Head<BinB>::res>, Bin0>::res,
        typename BitwiseAnd<
            typename Tail<BinA>::res,
            typename Tail<BinB>::res
        >::res
    >::res;
};


template<typename BinA>
struct BitwiseAnd<BinA, List<>> {
private:
    using op = AndOp<typename Head<BinA>::res, BitZ>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseAnd<
            typename Tail<BinA>::res,
            List<>
        >::res
    >::res;
};

template<typename BinB>
struct BitwiseAnd<List<>, BinB> {
private:
    using op = AndOp<BitZ, typename Head<BinB>::res>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseAnd<
            List<>,
            typename Tail<BinB>::res
        >::res
    >::res;
};

template<>
struct BitwiseAnd<List<>, List<>> {
    using res = List<>;
};
/* ------ Bitwise And ------ */



/* ------ Bitwise Or ------ */
template<typename BitA, typename BitB>
struct OrOp {};
template<> struct OrOp<BitZ, BitZ> { using res = BitZ; };
template<> struct OrOp<BitZ, BitO> { using res = BitO; };
template<> struct OrOp<BitO, BitZ> { using res = BitO; };
template<> struct OrOp<BitO, BitO> { using res = BitO; };

template<typename BinA, typename BinB>
struct BitwiseOr {
private:
    using op = OrOp<typename Head<BinA>::res, typename Head<BinB>::res>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseOr<
            typename Tail<BinA>::res,
            typename Tail<BinB>::res
        >::res
    >::res;
};

template<typename BinA>
struct BitwiseOr<BinA, List<>> {
private:
    using op = OrOp<typename Head<BinA>::res, BitZ>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseOr<
            typename Tail<BinA>::res,
            List<>
        >::res
    >::res;
};

template<typename BinB>
struct BitwiseOr<List<>, BinB> {
private:
    using op = OrOp<BitZ, typename Head<BinB>::res>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseOr<
            List<>,
            typename Tail<BinB>::res
        >::res
    >::res;
};

template<>
struct BitwiseOr<List<>, List<>> {
    using res = List<>;
};
/* ------ Bitwise Or ------ */



/* ------ Bitwise Xor ------ */
template<typename BitA, typename BitB>
struct XorOp {};
template<> struct XorOp<BitZ, BitZ> { using res = BitZ; };
template<> struct XorOp<BitZ, BitO> { using res = BitO; };
template<> struct XorOp<BitO, BitZ> { using res = BitO; };
template<> struct XorOp<BitO, BitO> { using res = BitZ; };

template<typename BinA, typename BinB>
struct BitwiseXor {
private:
    using op = XorOp<typename Head<BinA>::res, typename Head<BinB>::res>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseXor<
            typename Tail<BinA>::res,
            typename Tail<BinB>::res
        >::res
    >::res;
};

template<typename BinA>
struct BitwiseXor<BinA, List<>> {
private:
    using op = XorOp<typename Head<BinA>::res, BitZ>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseXor<
            typename Tail<BinA>::res,
            List<>
        >::res
    >::res;
};

template<typename BinB>
struct BitwiseXor<List<>, BinB> {
private:
    using op = XorOp<BitZ, typename Head<BinB>::res>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename BitwiseXor<
            List<>,
            typename Tail<BinB>::res
        >::res
    >::res;
};

template<>
struct BitwiseXor<List<>, List<>> {
    using res = List<>;
};
/* ------ Bitwise Xor ------ */



/* ------ Binary Equality ------ */
template<typename Bin>
struct EqTraverse {};

template<typename... Bits>
struct EqTraverse<List<BitZ, Bits...>> {
    using res = typename EqTraverse<List<Bits...>>::res;
};

template<typename... Bits>
struct EqTraverse<List<BitO, Bits...>> {
    using res = BitZ;
};

template<>
struct EqTraverse<List<>> {
    using res = BitO;
};

template<typename BinA, typename BinB>
struct Eq {
    using res = typename EqTraverse<
        typename BitwiseXor<BinA, BinB>::res
    >::res;
};
/* ------ Binary Equality ------ */



/* ------ Binary Addition ------ */
template<typename BitA, typename BitB, typename BitC>
struct AddOp {};
template<> struct AddOp<BitZ, BitZ, BitZ> { using res = BitZ; using cout = BitZ; };
template<> struct AddOp<BitZ, BitZ, BitO> { using res = BitO; using cout = BitZ; };
template<> struct AddOp<BitZ, BitO, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct AddOp<BitZ, BitO, BitO> { using res = BitZ; using cout = BitO; };
template<> struct AddOp<BitO, BitZ, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct AddOp<BitO, BitZ, BitO> { using res = BitZ; using cout = BitO; };
template<> struct AddOp<BitO, BitO, BitZ> { using res = BitZ; using cout = BitO; };
template<> struct AddOp<BitO, BitO, BitO> { using res = BitO; using cout = BitO; };

template<typename BinA, typename BinB, typename BitC>
struct AddC {
private:
    using op = AddOp<typename Head<BinA>::res, typename Head<BinB>::res, BitC>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename AddC<
            typename Tail<BinA>::res,
            typename Tail<BinB>::res,
            typename op::cout
        >::res
    >::res;
};

template<typename BinA>
struct AddC<BinA, List<>, BitO> {
private:
    using op = AddOp<BitZ, typename Head<BinA>::res, BitO>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename AddC<
            typename Tail<BinA>::res,
            List<>,
            typename op::cout
        >::res
    >::res;
};

template<typename BinA>
struct AddC<BinA, List<>, BitZ> {
    using res = BinA;
};

template<typename BinB>
struct AddC<List<>, BinB, BitO> {
private:
    using op = AddOp<BitZ, typename Head<BinB>::res, BitO>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename AddC<
            List<>,
            typename Tail<BinB>::res,
            typename op::cout
        >::res
    >::res;
};

template<typename BinB>
struct AddC<List<>, BinB, BitZ> {
    using res = BinB;
};

template<>
struct AddC<List<>, List<>, BitO> {
    using res = Bin1;
};

template<>
struct AddC<List<>, List<>, BitZ> {
    using res = List<>;
};

template<typename BinA, typename BinB>
struct Add {
    using res = typename AddC<BinA, BinB, BitZ>::res;
};
/* ------ Binary Addition ------ */



/* ------ Binary Increment ------ */
template<typename Bin>
struct Incr { using res = typename Add<Bin, Bin1>::res; };
/* ------ Binary Increment ------ */



/* ------ Binary Multiplication ------ */
template<typename BinA, typename BinB>
struct Mul {
    using res = typename Add<
        typename IfThenElse<typename Head<BinB>::res, BinA, Bin0>::res,
        typename Mul<
            typename Concat<Bin0, BinA>::res,
            typename Tail<BinB>::res
        >::res
    >::res;
};

template<typename BinA>
struct Mul<BinA, List<>> {
    using res = List<>;
};
/* ------ Binary Multiplication ------ */



/* ------ Binary Shift Right ------ */
// This actually shifts the bits to the left
// so that it follows the usual convention
// of shifting right being equivalent to
// dividing by two.
template<typename BinA, typename BinB, typename BinC, typename BitStop>
struct ShiftRC {};

template<typename BinA, typename BinB, typename BinC>
struct ShiftRC<BinA, BinB, BinC, BitZ> {
private:
    using op = Tail<BinA>;
    using BinCNext = typename Add<Bin1, BinC>::res;
public:
    using res = typename ShiftRC<
        typename op::res,
        BinB,
        BinCNext,
        typename Eq<BinB, BinCNext>::res
    >::res;
};

template<typename BinA, typename BinB, typename BinC>
struct ShiftRC<BinA, BinB, BinC, BitO> {
public:
    using res = BinA;
};

template<typename BinA, typename BinB>
struct ShiftR {
    using res = typename ShiftRC<
        BinA,
        BinB,
        Bin0,
        typename Eq<BinB, Bin0>::res
    >::res;
};
/* ------ Binary Shift Right ------ */



/* ------ Binary Shift Left ------ */
// This actually shifts the bits to the right
// so that it follows the usual convention
// of shifting left being equivalent to
// multiplying by two.
template<typename BinA, typename BinB, typename BinC, typename BitStop>
struct ShiftLC {};

template<typename BinA, typename BinB, typename BinC>
struct ShiftLC<BinA, BinB, BinC, BitZ> {
private:
    using op = Concat<Bin0, BinA>;
    using BinCNext = typename Add<Bin1, BinC>::res;
public:
    using res = typename ShiftLC<
        typename op::res,
        BinB,
        BinCNext,
        typename Eq<BinB, BinCNext>::res
    >::res;
};

template<typename BinA, typename BinB, typename BinC>
struct ShiftLC<BinA, BinB, BinC, BitO> {
public:
    using res = BinA;
};

template<typename BinA, typename BinB>
struct ShiftL {
    using res = typename ShiftLC<
        BinA,
        BinB,
        Bin0,
        typename Eq<BinB, Bin0>::res
    >::res;
};
/* ------ Binary Shift Left ------ */



/* ------ Index ------ */
template<typename L>
struct EveryOther {
private:
    using X  = typename Head<L>::res;
    using Xs = typename Tail<typename Tail<L>::res>::res;
public:
    using res = typename Concat<
        List<X>,
        typename EveryOther<Xs>::res
    >::res;
};

template<typename X>
struct EveryOther<List<X>> {
    using res = List<X>;
};

template<>
struct EveryOther<List<>> {
    using res = List<>;
};

template<typename L, typename Bit>
struct IndexOp {};
template<typename L> struct IndexOp<L, BitZ> { using res = typename EveryOther<L>::res; };
template<typename L> struct IndexOp<L, BitO> { using res = typename EveryOther<typename Tail<L>::res>::res; };

template<typename L, typename Bin>
struct Index {
private:
    using op = IndexOp<L, typename Head<Bin>::res>;
public:
    using res = typename Index<
        typename op::res,
        typename Tail<Bin>::res
    >::res;
};

template<typename L>
struct Index<L, List<>> {
    using res = typename Head<L>::res;
};
/* ------ Index ------ */

/* ------ Index Set ------ */
template<typename L, typename I, typename V, typename C, typename BitStop>
struct IndexSetC {};

template<typename L, typename I, typename V, typename C>
struct IndexSetC<L, I, V, C, BitZ> {
private:
    using NextC = typename Add<C, Bin1>::res;
public:
    using res = typename Concat<
        List<typename Head<L>::res>,
        typename IndexSetC<
            typename Tail<L>::res,
            I,
            V,
            NextC,
            typename Eq<I, NextC>::res
        >::res
    >::res;
};

template<typename I, typename V, typename C>
struct IndexSetC<List<>, I, V, C, BitZ> {
private:
    using NextC = typename Add<C, Bin1>::res;
public:
    using res = typename Concat<
        List<>,
        typename IndexSetC<
            List<>,
            I,
            V,
            NextC,
            typename Eq<I, NextC>::res
        >::res
    >::res;
};

template<typename L, typename I, typename V, typename C>
struct IndexSetC<L, I, V, C, BitO> {
    using res = typename Concat<
        List<V>,
        typename Tail<L>::res
    >::res;
};

template<typename L, typename I, typename V>
struct IndexSet {
    using res = typename IndexSetC<
        L,
        I,
        V,
        Bin0,
        typename Eq<I, Bin0>::res
    >::res;
};
/* ------ Index Set ------ */



/* ------ VM Stuff ------ */
template<typename PC, typename R, typename M>
struct VMState {};

// TODO: add a way to print out string
template<typename M, typename I, typename C>
struct VMHalt {
    static void output();
};

template<typename M, typename I>
struct VMHalt<M, I, Bin0> {
    static void output();
};

template<typename M, typename I>
void VMHalt<M, I, Bin0>::output() {}

template<typename M, typename I, typename C>
void VMHalt<M, I, C>::output() {
    std::uint8_t c = (std::uint8_t)(ToInt<typename Index<M, I>::res>::res);
    std::cout << c;

    using NextI = typename Add<I, Bin1>::res;
    using NextC = typename RemoveTrailingZero<typename Index<M, NextI>::res>::res;
    VMHalt<M, NextI, NextC>::output();
}



template<typename State>
struct VMLookupInstr {};

template<typename PC, typename R, typename M>
struct VMLookupInstr<VMState<PC, R, M>> {
    using res = typename RemoveTrailingZero<typename Index<M, PC>::res>::res;
};

template<typename State, typename Instruction>
struct VMExecuteInstr {};

// halt Reg0
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin0> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg0Content = typename Index<R, Reg0Index>::res;
    using MemContent  = typename Index<M, Reg0Content>::res;
public:
    using res = VMHalt<M, Reg0Content, MemContent>;
};

// movi Reg0, #Imm
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin1> {
private:
    using Reg0Index = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Immediate = typename Index<M, typename Add<PC, Bin2>::res>::res;
public:
    using res = VMState<
        typename Add<PC, Bin3>::res,
        typename IndexSet<R, Reg0Index, Immediate>::res,
        M
    >;
};

// movr Reg0, Reg1
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin2> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
public:
    using res = VMState<
        typename Add<PC, Bin3>::res,
        typename IndexSet<R, Reg0Index, Reg1Content>::res,
        M
    >;
};

// ldr Reg0, Reg1
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin3> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using MemContent  = typename Index<M, Reg1Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin3>::res,
        typename IndexSet<R, Reg0Index, MemContent>::res,
        M
    >;
};

// str Reg0, Reg1
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin4> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg0Content = typename Index<R, Reg0Index>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
public:
    using res = VMState<
        typename Add<PC, Bin3>::res,
        R,
        typename IndexSet<M, Reg1Content, Reg0Content>::res
    >;
};

// add Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin5> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename Add<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// mul Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin6> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename Mul<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// not Reg0, Reg1
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin7> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Res         = typename BitwiseNot<Reg1Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin3>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// and Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin8> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename BitwiseAnd<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// or Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, Bin9> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename BitwiseOr<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// xor Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, BinA> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename BitwiseXor<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// shl Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, BinB> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename ShiftL<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// shr Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, BinC> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using Res         = typename ShiftR<Reg1Content, Reg2Content>::res;
public:
    using res = VMState<
        typename Add<PC, Bin4>::res,
        typename IndexSet<R, Reg0Index, Res>::res,
        M
    >;
};

// jmp Reg0
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, BinD> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg0Content = typename Index<R, Reg0Index>::res;
public:
    using res = VMState<
        Reg0Content,
        R,
        M
    >;
};

// jeq Reg0, Reg1, Reg2
template<typename PC, typename R, typename M>
struct VMExecuteInstr<VMState<PC, R, M>, BinE> {
private:
    using Reg0Index   = typename Index<M, typename Add<PC, Bin1>::res>::res;
    using Reg1Index   = typename Index<M, typename Add<PC, Bin2>::res>::res;
    using Reg2Index   = typename Index<M, typename Add<PC, Bin3>::res>::res;
    using Reg0Content = typename Index<R, Reg0Index>::res;
    using Reg1Content = typename Index<R, Reg1Index>::res;
    using Reg2Content = typename Index<R, Reg2Index>::res;
    using JmpAddr     = typename IfThenElse<
        typename Eq<Reg0Content, Reg1Content>::res,
        Reg2Content,
        typename Add<PC, Bin4>::res
    >::res;
public:
    using res = VMState<
        JmpAddr,
        R,
        M
    >;
};

template<typename State>
struct VMStep {
private:
    using Instruction = typename VMLookupInstr<State>::res;
public:
    using res = typename VMExecuteInstr<State, Instruction>::res;
};

template<typename State>
struct VMStepUntilHalt {
    using res = typename VMStepUntilHalt<typename VMStep<State>::res>::res;
};

template<typename M, typename I, typename C>
struct VMStepUntilHalt<VMHalt<M, I, C>> {
    using res = VMHalt<M, I, C>;
};


using ProgramCounter = List<BitZ>;
using Registers = List<List<BitZ>,List<BitZ>,List<BitZ>,List<BitZ>, List<BitZ,BitZ,BitZ,BitO,BitO,BitO,BitO,BitZ,BitZ,BitO>,List<BitZ,BitZ,BitZ,BitO,BitO,BitO,BitO,BitZ,BitZ,BitO>>;
using InitialMemory = List<
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitZ,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitO,BitZ,BitO,BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitZ,BitO,BitZ,BitO,BitO,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitO,BitZ,BitZ,BitO,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO,BitO,BitZ,BitO,BitO,BitO,BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitZ,BitO,BitZ,BitO,BitO,BitZ,BitZ,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO,BitO,BitO,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitZ,BitO,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitO>,
    List<BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO,BitO,BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO,BitO,BitZ,BitZ,BitZ,BitZ,BitZ,BitO,BitO,BitZ,BitZ,BitZ,BitO,BitO,BitO,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitZ,BitO,BitZ,BitO,BitO,BitZ,BitZ,BitO,BitO,BitO,BitO,BitZ,BitO,BitO,BitO,BitZ,BitO,BitO,BitZ,BitZ,BitZ,BitO,BitO,BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitO,BitO,BitO,BitO,BitZ,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitO,BitO,BitZ,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO,BitZ,BitO,BitO,BitZ,BitO,BitO>,
    List<BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitO,BitO,BitO,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitO,BitO,BitZ,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitZ>,
    List<BitZ>,
    List<BitO,BitZ,BitZ,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO,BitO,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO,BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitO,BitO,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitZ,BitO,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitZ,BitZ,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitZ,BitO,BitO,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO,BitZ,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitZ,BitZ,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitO,BitZ,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitO,BitO,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitO,BitO,BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitO,BitZ,BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitO,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitO,BitO,BitO,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO,BitO,BitO,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO,BitO,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitZ,BitO,BitO,BitO>,
    List<BitO,BitO,BitO,BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO,BitO,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitO,BitZ,BitO,BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitO,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitZ,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitO,BitO,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO,BitZ,BitO,BitO>,
    List<BitO,BitO,BitO,BitO,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitO,BitO,BitZ,BitZ,BitO,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitO>,
    List<BitO,BitO>,
    List<BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitZ>,
    List<BitO>,
    List<BitZ>,
    List<BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitO,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitO,BitO,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitO,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitO,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitO,BitZ,BitO>,
    List<BitZ,BitO,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitO>,
    List<BitZ,BitZ,BitO>,
    List<BitZ>,
    List<BitZ,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitO>,
    List<BitO,BitO,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitZ,BitO>,
    List<BitZ,BitZ,BitO,BitO>,
    List<BitO>,
    List<BitZ,BitO,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitO,BitZ,BitO,BitO>,
    List<BitO,BitO,BitO,BitO>,
    List<BitO,BitO,BitO>,
    List<BitO,BitO,BitZ,BitO>,
    List<BitZ,BitO,BitO>,
    List<BitO,BitZ,BitZ,BitO>,
    List<BitO,BitO,BitO>,
    List<BitZ,BitZ,BitZ,BitO>,
    List<BitZ,BitO>,
    List<BitZ>,
    List<BitO,BitO>,
    List<BitO>
>;
using Input = List<
    // Your Input Here!
    Bin3,
    Bin1,
    Bin0,
    Bin1,
    Bin2,
    Bin3,
    Bin2,
    Bin0,
    Bin1,
    Bin3,
    Bin0,
    Bin2,
    Bin0
>;
using StackSpace = List<
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>,
    List<BitZ>
>;

/* ------ VM Stuff ------ */


int main() {
    VMStepUntilHalt<VMState<ProgramCounter, Registers, typename Concat<InitialMemory, typename Concat<Input, StackSpace>::res>::res>>::res::output();
}
