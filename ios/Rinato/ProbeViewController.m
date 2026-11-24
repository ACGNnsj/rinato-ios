#import "ProbeViewController.h"
#import <Metal/Metal.h>
#import <MetalKit/MetalKit.h>
#import "MetalProbeRenderer.h"
#import "NativeProbe.h"
#import "ProbeLog.h"

@interface ProbeViewController ()
@property(nonatomic, strong) MTKView *metalView;
@property(nonatomic, strong) UITextView *logView;
@property(nonatomic, strong) MetalProbeRenderer *renderer;
@property(nonatomic, assign) BOOL probesRan;
@end

@implementation ProbeViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = UIColor.blackColor;

    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    if (device == nil) {
        [[ProbeLog shared] line:@"PROBE metal_device=FAILED reason=MTLCreateSystemDefaultDevice_returned_nil"];
    } else {
        [[ProbeLog shared] line:@"PROBE metal_device=%s", device.name.UTF8String ?: "unknown"];
        [[ProbeLog shared] line:@"PROBE metal_family_apple7=%s",
            [device supportsFamily:MTLGPUFamilyApple7] ? "yes" : "no"];
        [[ProbeLog shared] line:@"PROBE metal_family_apple8=%s",
            [device supportsFamily:MTLGPUFamilyApple8] ? "yes" : "no"];
    }

    self.metalView = [[MTKView alloc] initWithFrame:self.view.bounds device:device];
    self.metalView.autoresizingMask = UIViewAutoresizingFlexibleWidth |
                                      UIViewAutoresizingFlexibleHeight;
    [self.view addSubview:self.metalView];
    if (device != nil) {
        self.renderer = [[MetalProbeRenderer alloc] initWithView:self.metalView];
    }

    self.logView = [[UITextView alloc] initWithFrame:CGRectZero];
    self.logView.editable = NO;
    self.logView.selectable = YES;
    self.logView.backgroundColor = [UIColor colorWithWhite:0.0 alpha:0.72];
    self.logView.textColor = UIColor.whiteColor;
    self.logView.font = [UIFont monospacedSystemFontOfSize:9 weight:UIFontWeightRegular];
    self.logView.textContainerInset = UIEdgeInsetsMake(24, 10, 10, 10);
    self.logView.autoresizingMask = UIViewAutoresizingFlexibleWidth |
                                    UIViewAutoresizingFlexibleHeight;
    [self.view addSubview:self.logView];
}

- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    // Keep the top 45% uncovered so a screenshot shows the raw Metal clear colour,
    // with the probe log readable underneath.
    CGRect bounds = self.view.bounds;
    CGFloat logHeight = CGRectGetHeight(bounds) * 0.55;
    self.logView.frame = CGRectMake(0, CGRectGetHeight(bounds) - logHeight,
                                    CGRectGetWidth(bounds), logHeight);
}

- (void)viewDidAppear:(BOOL)animated {
    [super viewDidAppear:animated];
    if (self.probesRan) {
        return;
    }
    self.probesRan = YES;

    __weak ProbeViewController *weakSelf = self;
    void (^sink)(NSString *) = ^(NSString *line) {
        [[ProbeLog shared] line:@"%@", line];
        [weakSelf refreshLog];
    };

    [[ProbeLog shared] line:@"PROBE session_start=%@", NSDate.date.description];

    [NativeProbe runAllWithLog:sink];

    self.renderer.onFirstPresent = ^(CGSize size, NSUInteger presents) {
        [weakSelf refreshLog];
        [[ProbeLog shared] line:@"PROBE screenshot_hint=first_frame_is_the_Metal_clear_color"];
        [weakSelf refreshLog];
    };
    [self.renderer start];
    [self refreshLog];
}

- (void)refreshLog {
    self.logView.text = [ProbeLog shared].text;
}

@end
