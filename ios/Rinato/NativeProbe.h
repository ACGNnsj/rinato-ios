#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Host-side M0 measurements. Each one is independent and records its real
/// outcome; a failure keeps the verbatim errno text and is never turned into a
/// success it did not observe.
@interface NativeProbe : NSObject

/// Emits "PROBE key=value" lines through the supplied sink.
+ (void)runAllWithLog:(void (^)(NSString *line))log;

@end

NS_ASSUME_NONNULL_END
