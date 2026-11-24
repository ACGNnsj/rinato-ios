#import <MetalKit/MetalKit.h>

NS_ASSUME_NONNULL_BEGIN

/// Clears the drawable to a fixed colour and counts real presents, so a screenshot
/// can be tied to a specific frame number instead of "the app looked fine".
@interface MetalProbeRenderer : NSObject <MTKViewDelegate>

@property(nonatomic, readonly) NSUInteger presentCount;
@property(nonatomic, readonly) CGSize drawableSize;
@property(nonatomic, copy, nullable) void (^onFirstPresent)(CGSize drawableSize, NSUInteger presentCount);

- (instancetype)initWithView:(MTKView *)view;
- (void)start;

@end

NS_ASSUME_NONNULL_END
