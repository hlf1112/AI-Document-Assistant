package org.example.aiservice;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import java.time.Duration;

import org.springframework.web.multipart.MultipartFile;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import java.util.Map;

/**
 * AI 业务中枢控制器
 */
@RestController
@RequestMapping("/api")
@CrossOrigin // 支持跨域访问
public class ChatController {

    @Autowired
    private RestTemplate restTemplate;

    // 初始化 WebClient，用于处理流式响应
    private final WebClient webClient = WebClient.create("http://127.0.0.1:8000");

    /**
     * 1. 智能问答接口 (流式输出)
     * produces = MediaType.TEXT_EVENT_STREAM_VALUE 是实现打字机效果的关键
     */
    // 完整替换 askAi 方法
    @PostMapping(value = "/ask", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> askAi(@RequestBody Map<String, Object> request) {
        return webClient.post()
                .uri("/ai/chat")
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(String.class)
                .timeout(Duration.ofSeconds(60)) // 设置 60 秒总超时
                .retry(2)
                .doOnError(e -> System.err.println("流式转发异常: " + e.getMessage()))
                .onErrorResume(e -> Flux.just("【系统提示：检测到网络波动，请尝试刷新页面】"));
    }

    /**
     * 2. 文档学习接口 (普通 JSON 响应)
     */
    @PostMapping("/train")
    public Map<String, Object> trainAi(@RequestParam String filePath) {
        String pythonUrl = "http://127.0.0.1:8000/ai/upload";

        // 设置请求头，告知 Python 这是一个表单提交 (Form Data)
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);

        // 封装表单参数
        MultiValueMap<String, String> map = new LinkedMultiValueMap<>();
        map.add("file_path", filePath);

        // 构建请求实体
        HttpEntity<MultiValueMap<String, String>> entity = new HttpEntity<>(map, headers);

        // 发送 POST 请求并返回 Python 的结果
        return restTemplate.postForObject(pythonUrl, entity, Map.class);
    }

    /**
     * 新接口：处理文件上传
     * 流程：前端传文件 -> Java保存到临时目录 -> Java把路径发给Python -> Python解析
     */
    @PostMapping("/upload")
    public Map<String, Object> uploadFile(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return Map.of("error", "文件为空");
        }

        try {
            // 1. 确定保存文件的目录 (这里存在项目根目录下的 temp_uploads 文件夹中)
            // System.getProperty("user.dir") 获取当前项目路径
            String uploadDir = System.getProperty("user.dir") + File.separator + "temp_uploads";
            File dir = new File(uploadDir);
            if (!dir.exists()) {
                dir.mkdirs(); // 如果目录不存在，创建它
            }

            // 2. 将上传的文件保存到服务器本地
            String originalFilename = file.getOriginalFilename();
            // 防止文件名重复，你也可以在文件名前加UUID，这里简单处理直接用原名
            Path filePath = Paths.get(uploadDir, originalFilename);
            Files.write(filePath, file.getBytes());

            System.out.println("文件已保存至: " + filePath.toString());

            // 3. 调用 Python 接口 (复用原来的逻辑，只是这次传的是服务器上的绝对路径)
            String pythonUrl = "http://127.0.0.1:8000/ai/upload";

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);

            MultiValueMap<String, String> map = new LinkedMultiValueMap<>();
            // 把刚才保存的 绝对路径 传给 Python
            map.add("file_path", filePath.toAbsolutePath().toString());

            HttpEntity<MultiValueMap<String, String>> entity = new HttpEntity<>(map, headers);

            return restTemplate.postForObject(pythonUrl, entity, Map.class);

        } catch (IOException e) {
            e.printStackTrace();
            return Map.of("error", "文件上传失败: " + e.getMessage());
        }
    }

    /**
     * 新接口：重置知识库
     * 前端调用 /api/reset -> Java 转发给 Python /ai/reset
     */
    @PostMapping("/reset")
    public Map<String, Object> resetKnowledgeBase() {
        String pythonUrl = "http://127.0.0.1:8000/ai/reset";
        // 发送 POST 请求给 Python (不需要参数)
        return restTemplate.postForObject(pythonUrl, null, Map.class);
    }
}