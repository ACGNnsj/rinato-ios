#import "MetalProbeRenderer.h"
#import "ProbeLog.h"

@interface MetalProbeRenderer ()
@property(nonatomic, weak) MTKView *view;
@property(nonatomic, strong) id<MTLDevice> device;
@property(nonatomic, strong) id<MTLCommandQueue> queue;
@property(nonatomic, assign) BOOL started;
@end

@implementation MetalProbeRenderer

- (instancetype)initWithView:(MTKView *)view {
    self = [super init];
    if (self) {
        _view = view;
        _device = view.device;
        _queue = [_device newCommandQueue];
        view.delegate = self;
        view.colorPixelFormat = MTLPixelFormatBGRA8Unorm;
        view.clearColor = MTLClearColorMake(0.06, 0.42, 0.55, 1.0);
        view.enableSetNeedsDisplay = YES;
        view.paused = YES;
        view.framebufferOnly = YES;
    }
    return self;
}

- (void)start {
    self.started = YES;
    [self.view setNeedsDisplay];
}

- (void)mtkView:(MTKView *)view drawableSizeWillChange:(CGSize)size {
    [[ProbeLog shared] line:@"PROBE metal_drawable_changed=%.0fx%.0f", size.width, size.height];
}

- (void)drawInMTKView:(MTKView *)view {
    if (!self.started) {
        return;
    }
    id<CAMetalDrawable> drawable = view.currentDrawable;
    if (drawable == nil) {
        [[ProbeLog shared] line:@"PROBE metal_drawable=FAILED reason=currentDrawable_was_nil"];
        return;
    }

    CGSize size = CGSizeMake(drawable.texture.width, drawable.texture.height);
    MTLRenderPassDescriptor *pass = view.currentRenderPassDescriptor;
    if (pass == nil) {
        [[ProbeLog shared] line:@"PROBE metal_pass=FAILED reason=currentRenderPassDescriptor_was_nil"];
        return;
    }
    id<MTLCommandBuffer> buffer = [self.queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [buffer renderCommandEncoderWithDescriptor:pass];
    [encoder endEncoding];
    [buffer presentDrawable:drawable];
    [buffer commit];
    [buffer waitUntilCompleted];

    _presentCount += 1;
    _drawableSize = size;

    [[ProbeLog shared] line:@"PROBE metal_drawable=%.0fx%.0f", size.width, size.height];
    [[ProbeLog shared] line:@"PROBE metal_presents=%lu", (unsigned long)self.presentCount];
    [[ProbeLog shared] line:@"PROBE metal_clear_color=0.06,0.42,0.55,1.0"];
    [[ProbeLog shared] line:@"PROBE metal_gpu=%s",
        self.device.name.UTF8String ?: "unknown"];

    if (self.onFirstPresent != nil) {
        void (^callback)(CGSize, NSUInteger) = self.onFirstPresent;
        self.onFirstPresent = nil;
        callback(size, self.presentCount);
    }
}

@end
