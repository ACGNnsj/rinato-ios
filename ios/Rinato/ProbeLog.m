#import "ProbeLog.h"

@interface ProbeLog ()
@property(nonatomic, strong) NSMutableString *buffer;
@property(nonatomic, strong, nullable) NSURL *url;
@end

@implementation ProbeLog

+ (instancetype)shared {
    static ProbeLog *shared = nil;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ shared = [[ProbeLog alloc] init]; });
    return shared;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        _buffer = [NSMutableString string];
    }
    return self;
}

- (nullable NSURL *)fileURL {
    if (self.url != nil) {
        return self.url;
    }
    NSFileManager *manager = NSFileManager.defaultManager;
    NSURL *documents = [manager URLsForDirectory:NSDocumentDirectory
                                       inDomains:NSUserDomainMask].firstObject;
    if (documents == nil) {
        return nil;
    }
    NSURL *url = [documents URLByAppendingPathComponent:@"probe.log"];
    [manager createFileAtPath:url.path contents:nil attributes:nil];
    self.url = url;
    return url;
}

- (void)line:(NSString *)format, ... {
    va_list arguments;
    va_start(arguments, format);
    NSString *message = [[NSString alloc] initWithFormat:format arguments:arguments];
    va_end(arguments);

    @synchronized (self) {
        [self.buffer appendString:message];
        [self.buffer appendString:@"\n"];
    }
    NSLog(@"%@", message);

    NSURL *url = self.fileURL;
    if (url == nil) {
        return;
    }
    NSFileHandle *handle = [NSFileHandle fileHandleForWritingToURL:url error:NULL];
    if (handle == nil) {
        return;
    }
    [handle seekToEndOfFile];
    [handle writeData:[message dataUsingEncoding:NSUTF8StringEncoding]];
    [handle writeData:[@"\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [handle closeFile];
}

- (NSString *)text {
    @synchronized (self) {
        return [self.buffer copy];
    }
}

@end
