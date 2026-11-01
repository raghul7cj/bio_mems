close all
clear all


%% Parameters

filename = 'data_P3.csv';

tinj = [10, 45, 45, 60];
tinj = cumsum(tinj);
dt = 0.1; % s


%% Import data
M = readtable(filename);

idx = M{:,1};
Nswv = max(idx);

i_flow = M{idx==0, 4}*1e6;
t_flow = [0:dt:dt*(length(i_flow)-1)]';
Nt = length(t_flow);

t_swv = unique(M{idx>0, 2}); % s
for n = 1:Nswv 
    E_swv{n} = M{idx==n,3};
    i_swv{n} = M{idx==n,4}*1e6;
end

%% analysis

% Flow tracking

threshold_v = [1.5, 1.5, 1.5, 0.4, 0.4, 0.4];
count_flow = 0;
count_stop = 0;
count_inj = 1;

status(1) = 1;
idx_threshold = 1;

for n = 1:Nt
    di_raw(n) = NaN;
    di(n) = NaN;
    THRESHOLD(n) = threshold_v(idx_threshold); % variable threshold

    % Compute differential current
    if n > 10
        di_raw(n) = i_flow(n) - i_flow(n-10);
        di(n) = abs(mean(di_raw(n-9:n)));
    end

    % Check if flow detected
    if n==1 || status(n-1) > 0 
        if di(n) > THRESHOLD(n)
            count_flow = count_flow+1;
        else
            count_flow = 0;
        end
        % Need 10 counts above threshold to trigger 
        if count_flow >= 10
           status(n) = 0;
           count_flow = 0;
           idx_threshold = idx_threshold+1;
        else 
           status(n) = count_inj;
        end
    else % If ongoing flow
        status(n) = status(n-1);

        if di(n) < THRESHOLD(n)
            count_stop = count_stop+1;
        else 
            count_stop = 0;
        end

        if count_stop >= 100
            count_inj = count_inj+1;
            status(n) = count_inj;
        end
    end

end

% Signal tracking
for n = 1:Nswv
    x = E_swv{n};
    y = i_swv{n};
    idx = x > -0.2 & x < 0.15;
    x = x(idx);
    y = y(idx);
    bl = backcor(x, y, 2, 1e-3, 'ah');
    
    [~,~,~,height] = findpeaks(y-bl, x, 'MinPeakProminence', 1e-4, 'SortStr','descend');
    if ~isempty(height)  
        Signal(n) = height(1);
    else 
        Signal(n) = NaN;
    end
end

%% plot

figure(1)
hold on
xline(tinj, 'k--')
plot(t_flow, i_flow, 'k.')
hold off
xlabel('time (s)')
ylabel('current (uA)')


figure(10)

subplot(2,1,1)
hold on
xline(tinj, 'k--')
% yline(THRESHOLD, 'r--')
plot(t_flow, THRESHOLD, 'r--')
plot(t_flow, di, '-', 'Color', 'b' , 'MarkerSize', 3)
hold off
xlabel('time (s)')
ylabel('diff current (µA)')
set(gca, 'YScale', 'log', 'XColor', 'k', 'YColor', 'k', 'FontSize', 7)
ylim([0.1, 1000])

subplot(2,1,2)
hold on
xline(tinj, 'k--')
plot(t_flow, status, '-', 'Color', 'b', 'LineWidth', 1)
hold off
xlabel('time (s)')
ylabel('status')

%saveas(gcf,[filename, 'line.pdf'])

col = flip(plasma(Nswv));

figure(2)
hold on
for n = 1:Nswv
    plot(E_swv{n}, i_swv{n}, '-', 'LineWidth',1, 'Color', col(n,:))
end
xlabel('E (V)')
ylabel('i (uA)')
xlim([-0.2, 0.2])
ylim([0,80])

figure(200)
plot(t_swv, Signal, 'k.', 'MarkerSize', 6)
xlabel('time (s)')
ylabel('peak strength (uA)')
set(gca, 'XLim', [200, 1215], 'XColor', 'k', 'YColor', 'k', 'FontSize', 7)


return
%% 
%save('S_N1', 'Signal', 't_swv')