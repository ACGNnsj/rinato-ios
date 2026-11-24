#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Append-only probe log. Every line goes to stderr (visible in Console/idevicesyslog)
/// and to Documents/probe.log (visible in the Files app), and is kept in memory so the
/// screen can show exactly what was recorded.
@interface ProbeLog : NSObject

+ (instancetype)shared;

- (void)line:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
- (NSString *)text;
- (nullable NSURL *)fileURL;

@end

NS_ASSUME_NONNULL_END
