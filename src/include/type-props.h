#ifndef TYPE_PROPS_H
#define TYPE_PROPS_H 1

#include <limits.h>

#define TYPE_IS_INTEGER(TYPE) ((TYPE) 1.5 == (TYPE) 1)
#define TYPE_IS_SIGNED(TYPE) ((TYPE) 0 > (TYPE) -1)
#define TYPE_VALUE_BITS(TYPE) (sizeof(TYPE) * CHAR_BIT - TYPE_IS_SIGNED(TYPE))
#define TYPE_MINIMUM(TYPE) (TYPE_IS_SIGNED(TYPE) \
                            ? ~(TYPE)0 << TYPE_VALUE_BITS(TYPE) \
                            : 0)
#define TYPE_MAXIMUM(TYPE) (TYPE_IS_SIGNED(TYPE) \
                            ? ~(~(TYPE)0 << TYPE_VALUE_BITS(TYPE)) \
                            : (TYPE)-1)

#endif /* type-props.h */
